from dotenv import load_dotenv
import os
import sys
import subprocess
import re
import socket
import datetime

# Get the current date and time
current_time = datetime.datetime.now()

# Format the date and time
formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

# Extract command-line arguments
openrc_file = sys.argv[1]
tag = sys.argv[2]
ssh_key = sys.argv[3]

# Load environment variables from the OpenRC file
load_dotenv(openrc_file)

# Access the environment variables
username = os.getenv("OS_USERNAME")
password = os.getenv("OS_PASSWORD")
auth_url = os.getenv("OS_AUTH_URL")
# ... and so on
print(f"{formatted_time}: Starting deployment of {tag} using {openrc_file} for credentials. ")
# Define server names
server_names = ["node1", "node2", "node3", "bastion", "haproxy"]

network_list = "openstack network list"
network_name = subprocess.run(network_list, shell=True, capture_output=True, text=True).stdout

print(f"{formatted_time}: checking for nework in the OpenStack project..")
# Check if network exists
if "project" in network_name:
    network_name = "project"
    print(f"{formatted_time}: Network found")
else:
    # Create network
    create_network = f"openstack network create project"
    subprocess.run(create_network, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}: network project does not exists! creating a network..")

    # Create subnet
    create_subnet = f"openstack subnet create project-subnet --network project --subnet-range 10.0.1.0/27"
    subprocess.run(create_subnet, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}: creating a subnet for network..")

    # Create router
    create_router = f"openstack router create project-router"
    subprocess.run(create_router, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}: creating a router..")

    # Set external gateway for the router
    create_ext = f"openstack router set project-router --external-gateway ext-net"
    subprocess.run(create_ext, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}: creating a external gateway for router..")

    # Connect subnet to router
    connect = f"openstack router add subnet project-router project-subnet"
    subprocess.run(connect, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}:adding router to subnet..")

#create a key
key_pair = "openstack keypair list"
key_pair_name = subprocess.run(key_pair, shell=True, capture_output=True, text=True).stdout
        
if "prjct" in key_pair_name:
    key_pair_name = "projct"
    print(f"{formatted_time}: checking for {tag}_{key_pair_name} in the OpenStack project..")
    print(f"{formatted_time}: keypair found")
else:
    create_key=f"openstack keypair create --public-key {ssh_key} prjct"
    subprocess.run(create_key, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{formatted_time}: creating a key..")

# Check if the rules already exist
check_ssh_rule = "openstack security group rule list --protocol tcp --dst-port 22 --ingress default"
check_http_rule = "openstack security group rule list --protocol tcp --dst-port 80 --ingress default"
check_https_rule = "openstack security group rule list --protocol tcp --dst-port 443 --ingress default"

ssh_rule_exists = "22" in subprocess.run(check_ssh_rule, shell=True, capture_output=True, text=True).stdout
http_rule_exists = "80" in subprocess.run(check_http_rule, shell=True, capture_output=True, text=True).stdout
https_rule_exists = "443" in subprocess.run(check_https_rule, shell=True, capture_output=True, text=True).stdout

#fetchin localhost ip address
def get_ip_address():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

current_ip = get_ip_address()


if ssh_rule_exists and http_rule_exists and https_rule_exists:
    print(f"{formatted_time}: Rules already exist in the default security group.")
else:
    # Create the missing rules
    if not ssh_rule_exists:
        allow_ssh = f"openstack security group rule create --protocol tcp --dst-port 22 --remote-ip {current_ip} default"
        subprocess.run(allow_ssh, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not http_rule_exists:
        allow_http = "openstack security group rule create --protocol tcp --dst-port 80 default"
        subprocess.run(allow_http, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not https_rule_exists:
        allow_https = "openstack security group rule create --protocol tcp --dst-port 443 default"
        subprocess.run(allow_https, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"{formatted_time}: adding rules to default security group..")


# Create servers

node_ips = []
for server_name in server_names:
    check_server = f"openstack server show {server_name}"
    result = subprocess.run(check_server, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        # Server with the same name already exists
        print(f"{formatted_time}: Server '{server_name}' already exists.")
        continue  # Skip creating the server
    else:
        create_server = f"openstack server create --flavor b.1c1gb --network project --key-name prjct --boot-from-volume 8 --image e6cbd963-8c28-4551-a837-e3b85da5d7a1 --security-group default --wait {server_name}"
        subprocess.run(create_server, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{formatted_time}:Creating server {server_name}...")

    # Fetch the IP address of the server
    fetch_ip_command = f"openstack server show -f value -c addresses {server_name}"
    ip_address_output = subprocess.run(fetch_ip_command, shell=True, capture_output=True, text=True).stdout.strip()

    # Extract the IP address from the output using regex
    ip_address = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', ip_address_output)[0]

    # Append the IP address to the node_ips list
    node_ips.append(ip_address)
    
# Get floating IPs
floating_list = "openstack floating ip list"
floating_list_output = subprocess.run(floating_list, shell=True, capture_output=True, text=True).stdout

# Extract the floating IP addresses
ip_addresses = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', floating_list_output)

if len(ip_addresses) >= 2:
    print(f"{formatted_time}: found 2 floating ip's..")
    floating_ip_bastion = ip_addresses[0]
    floating_ip_haproxy = ip_addresses[1]
else:
    # Create two floating IP addresses
    # Create floating IP for Bastion
    print(f"{formatted_time}: did not found any floating ip's.. creating..")
    create_floating_ip_bastion = f"openstack floating ip create ext-net"
    subprocess.run(create_floating_ip_bastion, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Create floating IP for HAproxy
    create_floating_ip_haproxy = f"openstack floating ip create ext-net"
    subprocess.run(create_floating_ip_haproxy, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Get the newly created floating IPs
    floating_list_output = subprocess.run(floating_list, shell=True, capture_output=True, text=True).stdout
    ip_addresses = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', floating_list_output)

    if len(ip_addresses) >= 2:
        floating_ip_bastion = ip_addresses[0]
        floating_ip_haproxy = ip_addresses[1]
    else:
        print(f"{formatted_time}: Failed to fetch or create the floating IP addresses.")
        exit()

# Assign floating IPs to Bastion and HAproxy
add_floating_ip_bastion = f"openstack server add floating ip Bastion {floating_ip_bastion}"
add_floating_ip_haproxy = f"openstack server add floating ip HAproxy {floating_ip_haproxy}"
subprocess.run(add_floating_ip_bastion, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(add_floating_ip_haproxy, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"{formatted_time}: adding floating ips to HAproxy and Bastion")

print(f"{formatted_time}: all nodes are done..")

# Build SSH config file
ssh_config_content = f"""
Host bastion
  HostName {floating_ip_bastion}
  User Ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no

Host haproxy
  HostName {floating_ip_haproxy}
  User Ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node1
  HostName {node_ips[0]}
  User Ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node2
  HostName {node_ips[1]}
  User Ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node3
  HostName {node_ips[2]}
  User Ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no 
  ProxyJump bastion  
"""

ssh_config_file_path = "SSHconfig"  # Path to the SSH config file
with open(ssh_config_file_path, "w") as ssh_config_file:
    ssh_config_file.write(ssh_config_content)

print(f"{formatted_time}: Building base SSH config file, saved to SSHconfig (current folder)")

# Build hosts file
hosts_file_path = "hosts"
with open(hosts_file_path, "w") as hosts_file:
    hosts_file.write("[HAproxy]\n")
    hosts_file.write("haproxy \n")
    hosts_file.write("\n")

    hosts_file.write("[nodes]\n")
    hosts_file.write(f"node1\n")
    hosts_file.write(f"node2\n")
    hosts_file.write(f"node3\n")
    hosts_file.write("\n[all:vars]\nansible_user=Ubuntu \n")


# Run Ansible playbook for deplyoment
print(f"{formatted_time}: Running playbook")
ansible_playbook = f"ansible-playbook -i {hosts_file_path} --ssh-common-args='-F./{ssh_config_file_path}' site.yaml"

playbook = subprocess.run(ansible_playbook, shell=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if playbook.returncode == 0:
    print(f"")
else:
    print(f"{formatted_time}: Error executing playbook.")
# Run Ansible Test envionment playbook
ansible_playbook = f"ansible-playbook -i {hosts_file_path} --ssh-common-args='-F./{ssh_config_file_path}' site1.yaml"

playbook_execution = subprocess.run(ansible_playbook, shell=True)

if playbook_execution.returncode == 0:
    print(f"{formatted_time}: OK")
else:
    print(f"{formatted_time}: Error executing playbook.")


