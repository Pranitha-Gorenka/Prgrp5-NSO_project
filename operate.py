from dotenv import load_dotenv
import os
import sys
import subprocess
import re
import time
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

# Load environment variables from the OpenRC file
load_dotenv(openrc_file)

# Access the environment variables
username = os.getenv("OS_USERNAME")
password = os.getenv("OS_PASSWORD")
auth_url = os.getenv("OS_AUTH_URL")
# ... and so on

# Define server names
server_names = ["node1", "node2", "node3"]

while True:
    # Read server.conf to get the required number of nodes
    with open('server.conf', 'r') as file:
        config_lines = file.readlines()

    # Extract the number of nodes required from server.conf
    num_nodes = None
    for line in config_lines:
        if "num_nodes =" in line:
            num_nodes_match = re.search(r'num_nodes = (\d+)', line)
            if num_nodes_match:
                num_nodes = int(num_nodes_match.group(1))
            break

    # Calculate the number of new nodes to create
    if num_nodes is None:
        print(f"{formatted_time}: Unable to find the required number of nodes in server.conf.")
        sys.exit(1)

    print(f"{formatted_time}: Reading server.conf, we need {num_nodes} nodes.")
    
    result = subprocess.run("openstack server list -c Name -f value", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    existing_nodes = re.findall(r'^node\d+', result.stdout, re.MULTILINE)
    print(f"{formatted_time}: Checking solution, we have: {len(existing_nodes)} nodes.")
    
    if len(existing_nodes) == num_nodes:
        # Update the number of nodes in server.conf
        config_lines = [line.replace(f"num_nodes = {num_nodes}", f"num_nodes = {num_nodes + 1}") for line in config_lines]
        with open('server.conf', 'w') as file:
            file.writelines(config_lines)
        time.sleep(30)
        
    elif len(existing_nodes) < num_nodes:
        num_new_nodes = num_nodes - len(existing_nodes)
        print(f"{formatted_time}: Detecting lostnode : {num_new_nodes} .")
        
        # Create new nodes
        for i in range(num_new_nodes):
            new_node_number = len(existing_nodes) + i + 1
            new_node_name = f"node{new_node_number}"
            
            # Check if the new node name already exists
            while new_node_name in existing_nodes:
                new_node_number += 1
                new_node_name = f"node{new_node_number}"

            create_server = f"openstack server create --flavor b.1c1gb --network {tag}_network --key-name {tag}_key --boot-from-volume 8 --image e6cbd963-8c28-4551-a837-e3b85da5d7a1 --security-group {tag}_security-group --wait {new_node_name}"
            subprocess.run(create_server, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            existing_nodes.append(new_node_name)
            print(f"{formatted_time}: created : {tag}_{new_node_name}")
            
        # Fetch the IP addresses of the new nodes
        node_ips = []
        for new_node_name in existing_nodes:
            fetch_ip_command = f"openstack server show -f value -c addresses {new_node_name}"
            ip_address_output = subprocess.run(fetch_ip_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if ip_address_output.returncode == 0:
                ip_addresses = re.findall(r'\d+\.\d+\.\d+\.\d+', ip_address_output.stdout)
                if ip_addresses:
                    node_ips.append(ip_addresses[0])

        # Build hosts file
        with open('hosts', 'r') as file:
            host_lines = file.readlines()

        updated_host_lines = []
        for line in host_lines:
            updated_host_lines.append(line.strip())

        # Find the index of the [nodes] group in the hosts file
        nodes_index = -1
        for i, line in enumerate(updated_host_lines):
           if line.strip() == '[nodes]':
               nodes_index = i
               break

        if nodes_index != -1:
            # Insert the new nodes after the [nodes] group
            updated_host_lines.insert(nodes_index + 1, f'{new_node_name}')

        # Write the updated hosts file
        with open('hosts', 'w') as file:
            file.write("\n".join(updated_host_lines))
            
        # Update the SSH config file
        with open(f'{tag}_SSHconfig', 'r') as file:
            ssh_lines = file.readlines()

        updated_ssh_lines = []
        for line in ssh_lines:
            updated_ssh_lines.append(line)

        for new_node_name, node_ip in zip(existing_nodes[-num_new_nodes:], node_ips[-num_new_nodes:]):
            ip_address_line = f"  HostName {node_ip}"  # Indent the HostName line correctly
            host_entry_found = False

            for i, line in enumerate(updated_ssh_lines):
                if f"Host {new_node_name}" in line:
                    if "HostName" in updated_ssh_lines[i+1]:
                        updated_ssh_lines[i+1] = f"  HostName {node_ip}\n"
                    else:
                        updated_ssh_lines.insert(i+1, f"  HostName {node_ip}\n")
                        host_entry_found = True
                        break

            if not host_entry_found:
                updated_ssh_lines.append(f"\nHost {new_node_name}\n  HostName {node_ip}\n  User Ubuntu\n  IdentityFile ~/.ssh/authorized_keys\n  UserKnownHostsFile=/dev/null\n  StrictHostKeyChecking no\n  PasswordAuthentication no\n  ProxyJump bastion\n")

        with open(f'{tag}_SSHconfig', 'w') as file:
            file.writelines(updated_ssh_lines)

        print(f"{formatted_time}: Updated {tag}_SSHconfig") 
        
        # Run Ansible playbook for deployment
        print(f"{formatted_time}: Running playbook")
        ansible_playbook = f"ansible-playbook -i hosts --ssh-common-args='-F./{tag}_SSHconfig' site.yaml"

        playbook = subprocess.run(ansible_playbook, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if playbook.returncode == 0:
            print("")
        else:
            print(f"{formatted_time}: Error executing playbook.")

        # Run Ansible Test environment playbook
        ansible_playbook = f"ansible-playbook -i hosts --ssh-common-args='-F./SSHconfig' site.yaml"

        playbook_execution = subprocess.run(ansible_playbook, shell=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if playbook_execution.returncode == 0:
            print(f"{formatted_time}: OK")
        else:
            ansible_playbook1 = f"ansible-playbook -i hosts site.yaml"
            playbook_execution1 = subprocess.run(ansible_playbook1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if playbook_execution1.returncode == 0:
                print(f"{formatted_time}: OK")
            else:
                ansible_playbook2 = f"ansible-playbook site.yaml"
                playbook_execution2 = subprocess.run(ansible_playbook2, shell=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if playbook_execution2.returncode == 0:
                print(f"{formatted_time}: OK") 
        time.sleep(30)
       
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

        result = subprocess.run("openstack server list -c Name -f value ", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        existing_nodes_all = re.findall(r'^node\d+', result.stdout, re.MULTILINE)

        for i, node in enumerate(existing_nodes_all, start=1):
            response = requests.get(url, proxies={"http": floating_ip, "https": floating_ip})

            # Print the page content
            print(f"{formatted_time}: Response {i}: {response.content.decode()}")

        print(f"{formatted_time}: OK")
