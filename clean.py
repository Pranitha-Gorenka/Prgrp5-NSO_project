from dotenv import load_dotenv
import os
import subprocess
import sys
import re
import datetime

# Get the current date and time
current_time = datetime.datetime.now()

# Format the date and time
formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

def run_command(command):
    subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cleanup(openrc_file, ssh_key):
    # Load environment variables from the OpenRC file
    load_dotenv(openrc_file)
    print(f"{formatted_time}: cleaning up {tag} using {openrc_file} ")
    # Server names
    server_names = ["node1", "node2", "node3","node4","node5"]
    print(f"{formatted_time}: We have 5 nodes deleting them ")
    # Delete servers
    for server_name in server_names:
        run_command(f"openstack server delete {server_name}")
        print(f"{formatted_time}: deleting {server_name} .. ")
    print(f"{formatted_time}: Nodes are gone ")    
    # List subnets and extract subnet IDs
    subnet_list_output = subprocess.check_output("openstack subnet list", shell=True)
    subnet_ids = re.findall(r"\|\s+(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\s+\|", subnet_list_output.decode())

    # Remove subnets from router and delete them
    router_name = "project-router"  # Replace with your router name
    for subnet_id in subnet_ids:
        run_command(f"openstack router remove subnet {router_name} {subnet_id}")
        run_command(f"openstack subnet delete {subnet_id}")
    print(f"{formatted_time}: deleting subnet.. ")
    # Delete network
    network_name = "project"  
    run_command(f"openstack network delete {network_name}")
    print(f"{formatted_time}: deleting network.. ")
    
    # Delete router
    run_command(f"openstack router delete {router_name}")
    print(f"{formatted_time}: deleting router.. ")
    
    # Delete keypair
    keypair_name = "prjct"  
    run_command(f"openstack keypair delete {keypair_name}")
    print(f"{formatted_time}: deleting keypair.. ")
    
    # List floating IPs and extract floating IP IDs
#    floating_ip_list_output = subprocess.check_output("openstack floating ip list", shell=True)
#   floating_ip_ids = re.findall(r"\|\s+(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\s+\|", floating_ip_list_output.decode())

    # Delete floating IPs
#    for floating_ip_id in floating_ip_ids:
#       run_command(f"openstack floating ip delete {floating_ip_id}")
#       print(f"{formatted_time}: deleting floating ips")

    # List volumes and extract volume IDs
    volume_list_output = subprocess.check_output("openstack volume list", shell=True)
    volume_ids = re.findall(r"\|\s+(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\s+\|", volume_list_output.decode())

    # Delete volumes
    for volume_id in volume_ids:
        run_command(f"openstack volume delete {volume_id}")
    
    print(f"{formatted_time}: deleting volumes.. ") 

    print(f"{formatted_time}:cleaning done")
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"{formatted_time}: Usage: python3 cleanup.py <openrc> <tag>")
        sys.exit(1)

    openrc_file = sys.argv[1]
    tag = sys.argv[2]

    cleanup(openrc_file, tag)
