#!/usr/bin/env python3

from dotenv import load_dotenv
import os
import sys
import subprocess
import re
import socket
import datetime
import requests

# Get the current date and time
current_time = datetime.datetime.now()

# Format the date and time
formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

# Extract command-line arguments
openrc_file = sys.argv[1]
tag = sys.argv[2]
ssh_key = sys.argv[3]

# Check if the provided files exist
if not os.path.isfile(openrc_file):
    print(f"Error: File '{openrc_file}' does not exist.")
    sys.exit(1)

if not os.path.isfile(ssh_key):
    print(f"Error: File '{ssh_key}' does not exist.")
    sys.exit(1)
    
# Load environment variables from the OpenRC file
load_dotenv(openrc_file)

# Access the environment variables
username = os.getenv("OS_USERNAME")
password = os.getenv("OS_PASSWORD")
auth_url = os.getenv("OS_AUTH_URL")
# ... and so on
print(f"{formatted_time}: Starting deployment of {tag} using {openrc_file} for credentials. ")
# Define server names
server_names = ["node1", "node2", "node3", "proxy2", "proxy1", "bastion" ]

network_list = "openstack network list"
network_name = subprocess.run(network_list, shell=True, capture_output=True, text=True).stdout

print(f"{formatted_time}: checking for network in the OpenStack project..")
# Check if network exists
if f"{tag}_network" in network_name:
    network_name = f"{tag}_network"
    print(f"{formatted_time}: Network found")
else:
    # Create network
    create_network = f"openstack network create {tag}_network"
    execution1 = subprocess.run(create_network, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution1.returncode == 0:
        print(f"{formatted_time}: network {tag}_network does not exists! creating a network..")
    else: 
        print(f"{formatted_time}: {tag}_network not created..")
        sys.exit(1)
    
    # Create subnet
    create_subnet = f"openstack subnet create {tag}_network-subnet --network {tag}_network --subnet-range 10.0.1.0/27"
    execution2 = subprocess.run(create_subnet, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution2.returncode == 0:
        print(f"{formatted_time}: creating a {tag}_network-subnet for {tag}_network..")
    else:
        print(f"{formatted_time}: {tag}_network-subnet  not created..")
        sys.exit(1)
        
    # Create router
    create_router = f"openstack router create {tag}_network-router"
    execution3 = subprocess.run(create_router, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution3.returncode == 0:
        print(f"{formatted_time}: creating a router..")
    else:
        print(f"{formatted_time}: {tag}_router  not created..")
        sys.exit(1)
        
    # Set external gateway for the router
    create_ext = f"openstack router set {tag}_network-router --external-gateway ext-net"
    execution4 = subprocess.run(create_ext, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution4.returncode == 0:
        print(f"{formatted_time}: creating a external gateway for router..")
    else:
        print(f"{formatted_time}: external gateway not created..")
        sys.exit(1)
        
    # Connect subnet to router
    connect = f"openstack router add subnet {tag}_network-router {tag}_network-subnet"
    execution5 = subprocess.run(connect, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution5.returncode == 0:
        print(f"{formatted_time}: adding router to subnet..")
    else:
        print(f"{formatted_time}: router not added to subnet..")
        sys.exit(1)

#create a key
key_pair = "openstack keypair list"
key_pair_name = subprocess.run(key_pair, shell=True, capture_output=True, text=True).stdout
print(f"{formatted_time}: checking for {tag}_key in the OpenStack project..")
        
if f"{tag}_key" in key_pair_name:
    key_pair_name = f"{tag}_key"
    print(f"{formatted_time}: keypair found")
else:
    create_key=f"openstack keypair create --public-key {ssh_key} {tag}_key"
    execution6 = subprocess.run(create_key, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if execution6.returncode == 0:
        print(f"{formatted_time}: creating a {tag}_key..")
    else:
        print(f"{formatted_time}: {tag}_key not created..")
        sys.exit(1)  

#fetching localhost ip address
def get_ip_address():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

current_ip = get_ip_address()


# Create a new security group
security_group = "openstack security group list"
security_group_name = subprocess.run(security_group, shell=True, capture_output=True, text=True).stdout

print(f"{formatted_time}: checking for {tag}_security-group in the OpenStack project..")
        
if f"{tag}_security-group" in security_group_name:
    security_group_name = f"{tag}_security-group"
    print(f"{formatted_time}: {tag}_security-group found")
else:
    create_security_group = f"openstack security group create {tag}_security-group"
    execution7 = subprocess.run(create_security_group, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Add the required rules to the new security group
    create_ssh_rule = f"openstack security group rule create --protocol tcp --dst-port 22 {tag}_security-group"
    create_http_rule = f"openstack security group rule create --protocol tcp --dst-port 80 {tag}_security-group"
    create_https_rule = f"openstack security group rule create --protocol tcp --dst-port 443 {tag}_security-group"
    create_flask_rule = f"openstack security group rule create --protocol tcp --dst-port 5000 {tag}_security-group" 
    create_snmp_rule = f"openstack security group rule create --protocol udp --dst-port 6000 {tag}_security-group"
    create_snmpd_rule = f"openstack security group rule create --protocol udp --dst-port 161 {tag}_security-group"
    create_icmp_rule = f"openstack security group rule create --protocol icmp --dst-port 22 {tag}_security-group"

    subprocess.run(create_ssh_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_http_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_https_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_flask_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_snmp_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_snmpd_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(create_icmp_rule, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if execution7.returncode == 0:
        print(f"{formatted_time}: Created a  {tag}_security-group and added the required rules.")
    else:
        print(f"{formatted_time}: {tag}_security-group not created..")
        sys.exit(1)  
    

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
        create_server = f"openstack server create --flavor b.1c1gb --network {tag}_network --key-name {tag}_key --boot-from-volume 8 --image e6cbd963-8c28-4551-a837-e3b85da5d7a1 --security-group {tag}_security-group --wait {server_name}"
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
floating_ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', floating_list_output)
fixed_ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+', floating_list_output)

# Check if two floating IPs exist
if len(floating_ips) >= 2:
    print(f"{formatted_time}: Found 2 floating IPs.")
    floating_ip_bastion = floating_ips[0]
    floating_ip_proxy1 = floating_ips[1]
    
    # Assign floating IPs to servers
    assign_floating_ip_bastion = f"openstack server add floating ip bastion {floating_ip_bastion}"
    assign_floating_ip_proxy1 = f"openstack server add floating ip proxy1 {floating_ip_proxy1}"
    
    subprocess.run(assign_floating_ip_bastion, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(assign_floating_ip_proxy1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"{formatted_time}: Assigned floating IPs to bastion and proxy1.")
else:
    print(f"{formatted_time}: Did not find 2 floating IPs. Creating new ones...")
    
    # Create floating IP for Bastion
    create_floating_ip_bastion = "openstack floating ip create ext-net"
    subprocess.run(create_floating_ip_bastion, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Create floating IP for HAproxy
    create_floating_ip_proxy1 = "openstack floating ip create ext-net"
    subprocess.run(create_floating_ip_proxy1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Get the newly created floating IPs
    floating_list_output = subprocess.run(floating_list, shell=True, capture_output=True, text=True).stdout
    floating_ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', floating_list_output)

    if len(floating_ips) >= 2:
        floating_ip_bastion = floating_ips[0]
        floating_ip_proxy1 = floating_ips[1]
        
        # Assign floating IPs to servers
        assign_floating_ip_bastion = f"openstack server add floating ip bastion {floating_ip_bastion}"
        assign_floating_ip_proxy1 = f"openstack server add floating ip proxy1 {floating_ip_proxy1}"
    
        subprocess.run(assign_floating_ip_bastion, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(assign_floating_ip_proxy1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
        print(f"{formatted_time}: Assigned floating IPs to bastion and proxy1.")        
        
    else:
        print(f"{formatted_time}: Failed to fetch or create the floating IP addresses.")
        exit()

print(f"{formatted_time}: all nodes are done..")
print(floating_ip_bastion)
print(floating_ip_proxy1)


# Build SSH config file
ssh_config_content = f"""Host bastion
  HostName {floating_ip_bastion}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no

Host proxy1
  HostName {floating_ip_proxy1}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host proxy2
  HostName {node_ips[0]}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node1
  HostName {node_ips[1]}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node2
  HostName {node_ips[2]}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no
  ProxyJump bastion

Host node3
  HostName {node_ips[3]}
  User ubuntu
  IdentityFile ~/.ssh/authorized_keys
  UserKnownHostsFile=~/dev/null
  StrictHostKeyChecking no
  PasswordAuthentication no 
  ProxyJump bastion  
"""

ssh_config_file_path = f"{tag}_SSHconfig"  # Path to the SSH config file
with open(ssh_config_file_path, "w") as ssh_config_file:
    ssh_config_file.write(ssh_config_content)

print(f"{formatted_time}: Building base SSH config file, saved to {tag}_SSHconfig (current folder)")

# Build hosts file
hosts_file_path = "hosts"
with open(hosts_file_path, "w") as hosts_file:
    hosts_file.write("[Bastion]\n")
    hosts_file.write("bastion \n")

    hosts_file.write("\n[HAproxy]\n")
    hosts_file.write("proxy1 \n")
    hosts_file.write("proxy2 \n")
    hosts_file.write("\n")

    hosts_file.write("[nodes]\n")
    hosts_file.write(f"node1\n")
    hosts_file.write(f"node2\n")
    hosts_file.write(f"node3\n")
    hosts_file.write("\n[all:vars]\nansible_user=ubuntu \n")
    hosts_file.write("\n##REMOVED sshkey entry, handled by external SSH config file ##  \n")
    

# Run Ansible playbook for deplyoment
print(f"{formatted_time}: Running playbook")
ansible_playbook = f"ansible-playbook -i hosts --ssh-common-args='-F./{tag}_SSHconfig' site.yaml"
playbook_execution = subprocess.run(ansible_playbook, shell=True)

if playbook_execution.returncode == 0:
    print(f"{formatted_time}: OK")
else:
    ansible_playbook1 = f"ansible-playbook -i hosts site.yaml"
    playbook_execution1 = subprocess.run(ansible_playbook1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if playbook_execution1.returncode == 0:
        print(f"{formatted_time}: OK")
    else: 
        print(f"{formatted_time}: Error executing playbook.") 
           
# Get floating IPs
floating_list = "openstack server show proxy1 -c addresses -f value"
floating_list_output = subprocess.run(floating_list, shell=True, capture_output=True, text=True).stdout

# Extract the floating IP addresses
floating_ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', floating_list_output)
fixed_ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+', floating_list_output)

print(f"{formatted_time}: Validates Operation")
for floating_ip in floating_ips:
    print("")

# Define the URL to browse
url = "http://" + floating_ip

result = subprocess.run("openstack server list -c Name -f value", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
existing_nodes = re.findall(r'^node\d+', result.stdout, re.MULTILINE)

for i, node in enumerate(existing_nodes, start=1):
    response = requests.get(url, proxies={"http": floating_ip, "https": floating_ip})

    # Print the page content
    print(f"{formatted_time}: Response {i}: {response.content.decode()}")

print(f"{formatted_time}: OK")
