
import streamlit as st
import yaml
from netmiko import ConnectHandler
from datetime import datetime
from utils.cohere_parser import get_action_from_prompt, extract_config_commands
import difflib
import os

# Folder to store running configs
RUNNING_CONFIG_FOLDER = "running_configs"
if not os.path.exists(RUNNING_CONFIG_FOLDER):
    os.makedirs(RUNNING_CONFIG_FOLDER)

st.set_page_config(page_title="Network Assistant", layout="centered")

# Load devices from YAML
@st.cache_data
def load_devices():
    with open("devices.yaml", "r") as file:
        data = yaml.safe_load(file)
    return data["devices"]

# Device setup
devices_list = load_devices()
device_options = [f"{d['name']} ({d['ip']})" for d in devices_list]
devices_dict = {f"{d['name']} ({d['ip']})": d for d in devices_list}

# File setup
def list_files_in_directory(directory_path):
    try:
        # List all entries in the given directory
        entries = os.listdir(directory_path)
        
        # Filter only files
        files = [entry for entry in entries if os.path.isfile(os.path.join(directory_path, entry))]
        
        return files
    except FileNotFoundError:
        print(f"The directory '{directory_path}' does not exist.")
        return []
    except PermissionError:
        print(f"Permission denied to access '{directory_path}'.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    
# Example usage
directory = r'C:\Users\lenovo\Desktop\Cohere\running_configs'
file_options = list_files_in_directory(directory)
st.title("Network Assistant (Cohere-Powered)")
st.markdown("Enter a prompt like: 'audit R1', 'configure BGP on R2', 'remove OSPF from R3'")

# Inputs
selected_devices = st.multiselect("Select Devices", options=device_options)
prompt = st.text_area("Enter your network request:", height=100)
run = st.button("Run Configuration")
run2 = st.button("Take Backup")
run4 = st.button("Restore this file")
available_config = st.multiselect("Select backup file",options=file_options)

if run4 and selected_devices and available_config:
    for device_label in selected_devices:
        print(device_label)
        device_info = devices_dict[device_label]
        try:
            conn_params = {
                "device_type": device_info["device_type"],
                "ip": device_info["ip"],
                "username": device_info["username"],
                "password": device_info["password"],
                }
            st.subheader(f"🔧 DEVICE: {device_label}")
            with ConnectHandler(**conn_params) as conn:
                conn.enable()

            #  find the backup file
                for file_label in available_config:
                    abs = f"{RUNNING_CONFIG_FOLDER}/{file_label}"
                    conn.send_config_from_file(abs)
                    st.success("✅ File Uploaded.")

        except Exception as e:
            st.error(f"❌ Error on {device_label}: {str(e)}")
       
if run and selected_devices and prompt:
    with st.spinner(" Processing your request..."):
        response_text = get_action_from_prompt(prompt)
        commands = extract_config_commands(response_text)

        st.subheader("📋 Configuration to be Applied")
        st.code("\n".join(commands), language="shell")

        for device_label in selected_devices:
            device_info = devices_dict[device_label]
            try:
                conn_params = {
                    "device_type": device_info["device_type"],
                    "ip": device_info["ip"],
                    "username": device_info["username"],
                    "password": device_info["password"],
                }

                st.subheader(f"🔧 DEVICE: {device_label}")
                with ConnectHandler(**conn_params) as conn:
                    conn.enable()

                    # Capture old config
                    old_config = conn.send_command("show running-config")
                    old_filename = f"{RUNNING_CONFIG_FOLDER}/old_running_{device_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(old_filename, "w") as f:
                        f.write(old_config)

                    # Apply configuration
                    if any("no " not in cmd and not cmd.startswith("show") for cmd in commands):
                        conn.send_config_set(commands)
                        st.success("✅ Configuration applied.")

                    # Show command outputs
                    for cmd in commands:
                        if cmd.startswith("show"):
                            output = conn.send_command(cmd)
                            st.code(output, language="shell")

                    # Capture new config
                    new_config = conn.send_command("show running-config")
                    new_filename = f"{RUNNING_CONFIG_FOLDER}/new_running_{device_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(new_filename, "w") as f:
                        f.write(new_config)
                    st.success(f"💾 New running config saved: {new_filename}")

                    # Show differences
                    st.markdown("🆚 **Changes in Configuration:**")
                    diff = difflib.unified_diff(
                        old_config.splitlines(),
                        new_config.splitlines(),
                        fromfile='Before',
                        tofile='After',
                        lineterm=''
                    )
                    diff_output = '\n'.join(diff)
                    if diff_output:
                        st.code(diff_output, language="diff")
                    else:
                        st.info("ℹ️ No changes detected.")
            except Exception as e:
                st.error(f"❌ Error on {device_label}: {str(e)}")       

if run2 and selected_devices:
    with st.spinner(" Processing your request..."):
        for device_label in selected_devices:
            device_info = devices_dict[device_label]
            try:
                conn_params = {
                    "device_type": device_info["device_type"],
                    "ip": device_info["ip"],
                    "username": device_info["username"],
                    "password": device_info["password"],
                }

                st.subheader(f"🔧 DEVICE: {device_label}")
                with ConnectHandler(**conn_params) as conn:
                    conn.enable()

                    # Capture old config
                    old_config = conn.send_command("show running-config")
                    old_filename = f"{RUNNING_CONFIG_FOLDER}/Config_{device_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                    with open(old_filename, "w") as f:
                        f.write(old_config)


                    # Show differences
                    st.markdown("🆚**Backup taken successfully**")
            except Exception as e:
                st.error(f"❌ Error on {device_label}: {str(e)}")
