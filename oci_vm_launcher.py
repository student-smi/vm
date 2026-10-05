import os
import sys
import time
import datetime
import subprocess
import configparser

# Configure Windows/Linux console for UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import oci
except ImportError:
    print("[ERROR] 'oci' Python package is not installed.")
    print("Please run: pip install oci requests")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None

try:
    import winsound
except ImportError:
    winsound = None

# ==========================================
# CONFIGURATION SETTINGS
# ==========================================
CONFIG_FILE = "oci_config.ini"
DEFAULT_KEY_FILE = "oci_api_key.pem"
SSH_KEY_NAME = "oci_vm_key"
INSTANCE_NAME = "Free-VM-12GB-Mumbai"
OCPUS = 2                 # 2 OCPUs (Always Free limit allows up to 4)
MEMORY_IN_GBS = 12        # 12 GB RAM requested
BOOT_VOLUME_GB = 50       # 50 GB Boot Volume (Always Free up to 200 GB)
RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", "60"))  # Seconds between attempts
OS_PREFERENCE = "Ubuntu"  # "Ubuntu" or "Oracle-Linux"

# Run limit in minutes (useful for GitHub Actions to prevent sudden runner kills)
MAX_RUN_MINUTES = int(os.environ.get("MAX_RUN_MINUTES", "0"))  # 0 means infinite loop


def print_banner():
    banner = r"""
============================================================
       🚀 OCI Always Free ARM VM Auto-Launcher (Mumbai) 🚀
============================================================
 Specs: VM.Standard.A1.Flex | 2 OCPU | 12 GB RAM | ap-mumbai-1
============================================================
"""
    print(banner)


def send_telegram_alert(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    if not requests:
        print("⚠️ requests package missing, cannot send Telegram notification.")
        return

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
        print("📲 Telegram notification sent successfully!")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")


def load_config_and_keys():
    """Load config from Environment Variables (GitHub Actions) or oci_config.ini (Local)."""
    # Check if Environment variables are set (e.g. GitHub Actions)
    if os.environ.get("OCI_USER") and os.environ.get("OCI_TENANCY"):
        print("⚙️ Loading configuration from Environment Variables...")
        key_content = os.environ.get("OCI_KEY_CONTENT")
        key_file_path = os.environ.get("OCI_KEY_FILE", DEFAULT_KEY_FILE)

        if key_content and not os.path.exists(key_file_path):
            with open(key_file_path, "w", encoding="utf-8") as f:
                f.write(key_content.strip())
            print(f"✅ Created temporary key file from secret.")

        config = {
            "user": os.environ.get("OCI_USER"),
            "fingerprint": os.environ.get("OCI_FINGERPRINT"),
            "tenancy": os.environ.get("OCI_TENANCY"),
            "region": os.environ.get("OCI_REGION", "ap-mumbai-1"),
            "key_file": os.path.abspath(key_file_path)
        }
    else:
        # Load from oci_config.ini
        if not os.path.exists(CONFIG_FILE):
            print(f"❌ Config file '{CONFIG_FILE}' not found!")
            sys.exit(1)

        cp = configparser.ConfigParser()
        cp.read(CONFIG_FILE)
        if "DEFAULT" not in cp:
            print(f"❌ Invalid '{CONFIG_FILE}'. Missing [DEFAULT] section.")
            sys.exit(1)

        key_file = cp["DEFAULT"].get("key_file", DEFAULT_KEY_FILE)
        if not os.path.isabs(key_file):
            key_file = os.path.abspath(key_file)

        if not os.path.exists(key_file):
            print("\n" + "=" * 60)
            print("⚠️  MISSING PRIVATE KEY FILE (.pem)!")
            print("=" * 60)
            print(f"File expected at: {key_file}")
            print("\nતમારે Oracle Console માંથી જે Private Key (.pem file) ડાઉનલોડ કરી છે,")
            print(f"તેને આ ફોલ્ડરમાં '{os.path.basename(key_file)}' નામથી મૂકો.")
            print("=" * 60 + "\n")
            return None, None

        config = {
            "user": cp["DEFAULT"].get("user"),
            "fingerprint": cp["DEFAULT"].get("fingerprint"),
            "tenancy": cp["DEFAULT"].get("tenancy"),
            "region": cp["DEFAULT"].get("region", "ap-mumbai-1"),
            "key_file": key_file
        }

    # Generate SSH Keypair for VM access if not already present
    pub_key_path = f"{SSH_KEY_NAME}.pub"
    priv_key_path = SSH_KEY_NAME

    if not os.path.exists(pub_key_path) or not os.path.exists(priv_key_path):
        print(f"🔑 Generating SSH keypair ({SSH_KEY_NAME})...")
        cmd = f'ssh-keygen -t rsa -b 4096 -f "{priv_key_path}" -N "" -q'
        res = subprocess.run(cmd, shell=True)
        if res.returncode != 0 or not os.path.exists(pub_key_path):
            print("❌ Failed to generate SSH key using ssh-keygen.")
            sys.exit(1)
        print("✅ Generated new SSH keypair for VM access.")

    with open(pub_key_path, "r", encoding="utf-8") as f:
        ssh_pub_key = f.read().strip()

    return config, ssh_pub_key


def get_oci_clients(config):
    """Initialize and validate OCI API clients."""
    oci.config.validate_config(config)

    identity_client = oci.identity.IdentityClient(config)
    compute_client = oci.core.ComputeClient(config)
    network_client = oci.core.VirtualNetworkClient(config)

    # Test authentication
    user = identity_client.get_user(config["user"]).data
    print(f"✅ Connected to Oracle Cloud successfully!")
    print(f"   👤 User: {user.name} ({user.email or 'No email'})")
    print(f"   🌐 Region: {config['region']}")
    print(f"   🏢 Tenancy: {config['tenancy']}")

    return identity_client, compute_client, network_client


def get_availability_domain(identity_client, compartment_id):
    """Get the first availability domain for the region."""
    ads = identity_client.list_availability_domains(compartment_id).data
    if not ads:
        raise RuntimeError("No Availability Domains found in compartment.")
    ad = ads[0].name
    print(f"   📍 Availability Domain: {ad}")
    return ad


def find_or_create_network(network_client, compartment_id):
    """Find an existing subnet or automatically create a quick VCN + Subnet."""
    print("🔍 Checking network configuration (VCN & Subnets)...")
    subnets = network_client.list_subnets(compartment_id).data
    for subnet in subnets:
        if subnet.lifecycle_state in ["AVAILABLE", "PROVISIONING"]:
            print(f"   ✅ Using existing Subnet: {subnet.display_name} ({subnet.id})")
            return subnet.id

    print("⚠️ No existing subnet found. Auto-creating VCN and Public Subnet...")
    vcn_details = oci.core.models.CreateVcnDetails(
        cidr_block="10.0.0.0/16",
        display_name="Auto-Free-VCN",
        compartment_id=compartment_id,
        dns_label="freevcn"
    )
    vcn = network_client.create_vcn(vcn_details).data
    print(f"   ✅ Created VCN: {vcn.display_name}")

    ig_details = oci.core.models.CreateInternetGatewayDetails(
        compartment_id=compartment_id,
        display_name="Auto-IGW",
        is_enabled=True,
        vcn_id=vcn.id
    )
    ig = network_client.create_internet_gateway(ig_details).data
    print(f"   ✅ Created Internet Gateway: {ig.display_name}")

    route_rule = oci.core.models.RouteRule(
        destination="0.0.0.0/0",
        destination_type="CIDR_BLOCK",
        network_entity_id=ig.id
    )
    rt = network_client.get_route_table(vcn.default_route_table_id).data
    update_rt_details = oci.core.models.UpdateRouteTableDetails(
        route_rules=[route_rule]
    )
    network_client.update_route_table(rt.id, update_rt_details)
    print("   ✅ Updated Default Route Table with 0.0.0.0/0 Internet rule.")

    subnet_details = oci.core.models.CreateSubnetDetails(
        cidr_block="10.0.0.0/24",
        compartment_id=compartment_id,
        display_name="Auto-Public-Subnet",
        vcn_id=vcn.id,
        route_table_id=rt.id,
        dns_label="subnet1"
    )
    new_subnet = network_client.create_subnet(subnet_details).data
    print(f"   ✅ Created Public Subnet: {new_subnet.display_name} ({new_subnet.id})")
    time.sleep(5)
    return new_subnet.id


def get_arm_image(compute_client, compartment_id, os_name="Ubuntu"):
    """Find the latest compatible ARM64 image."""
    print(f"🔍 Searching for latest {os_name} ARM64 image for VM.Standard.A1.Flex...")
    images = compute_client.list_images(
        compartment_id=compartment_id,
        shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED",
        sort_order="DESC"
    ).data

    chosen_image = None
    for img in images:
        name = img.display_name.lower()
        if os_name.lower() in name and "aarch64" in name:
            chosen_image = img
            break

    if not chosen_image:
        for img in images:
            if "aarch64" in img.display_name.lower():
                chosen_image = img
                break

    if not chosen_image and images:
        chosen_image = images[0]

    if not chosen_image:
        raise RuntimeError("No compatible ARM64 image found for VM.Standard.A1.Flex.")

    print(f"   ✅ Selected Image: {chosen_image.display_name} ({chosen_image.id})")
    return chosen_image.id, chosen_image.display_name


def play_success_sound():
    if winsound:
        try:
            for _ in range(5):
                winsound.Beep(1200, 300)
                winsound.Beep(1800, 400)
        except Exception:
            pass


def get_instance_public_ip(compute_client, network_client, compartment_id, instance_id):
    """Wait for instance to run and fetch its public IP."""
    print("⏳ Waiting for instance to transition to RUNNING state...", flush=True)
    max_wait = 180
    start = time.time()
    while time.time() - start < max_wait:
        inst = compute_client.get_instance(instance_id).data
        if inst.lifecycle_state == "RUNNING":
            break
        time.sleep(5)

    vnics = compute_client.list_vnic_attachments(
        compartment_id=compartment_id,
        instance_id=instance_id
    ).data

    if vnics:
        vnic = network_client.get_vnic(vnics[0].vnic_id).data
        return vnic.public_ip
    return None


def main():
    print_banner()

    config, ssh_pub_key = load_config_and_keys()
    if not config:
        return

    try:
        identity_client, compute_client, network_client = get_oci_clients(config)
    except Exception as e:
        print(f"❌ Failed to connect to OCI: {e}")
        return

    compartment_id = config["tenancy"]

    try:
        ad = get_availability_domain(identity_client, compartment_id)
        subnet_id = find_or_create_network(network_client, compartment_id)
        image_id, image_name = get_arm_image(compute_client, compartment_id, OS_PREFERENCE)
    except Exception as e:
        print(f"❌ Error during resource lookup: {e}")
        return

    print("\n" + "=" * 60)
    print("📋 TARGET INSTANCE CONFIGURATION:")
    print(f"   - Shape:           VM.Standard.A1.Flex (Always Free)")
    print(f"   - OCPUs:           {OCPUS}")
    print(f"   - Memory (RAM):    {MEMORY_IN_GBS} GB")
    print(f"   - Boot Volume:     {BOOT_VOLUME_GB} GB")
    print(f"   - OS:              {image_name}")
    print(f"   - Availability AD: {ad}")
    print(f"   - Retry Interval:  {RETRY_INTERVAL} seconds")
    if MAX_RUN_MINUTES > 0:
        print(f"   - Max Run Time:    {MAX_RUN_MINUTES} minutes")
    print("=" * 60)
    print("🔄 Starting retry loop. Script will keep trying until Oracle assigns capacity...")
    print("   (Press Ctrl + C anytime to stop)\n", flush=True)

    launch_details = oci.core.models.LaunchInstanceDetails(
        compartment_id=compartment_id,
        availability_domain=ad,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=float(OCPUS),
            memory_in_gbs=float(MEMORY_IN_GBS)
        ),
        display_name=INSTANCE_NAME,
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=image_id,
            boot_volume_size_in_gbs=BOOT_VOLUME_GB
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=subnet_id,
            assign_public_ip=True,
            display_name=f"{INSTANCE_NAME}-vnic"
        ),
        metadata={
            "ssh_authorized_keys": ssh_pub_key
        }
    )

    start_time = time.time()
    attempt = 1

    while True:
        # Check if max run minutes exceeded (for GitHub Actions)
        if MAX_RUN_MINUTES > 0:
            elapsed_minutes = (time.time() - start_time) / 60.0
            if elapsed_minutes >= MAX_RUN_MINUTES:
                print(f"\n⏱️ Reached max run limit of {MAX_RUN_MINUTES}m. Ending this run cleanly for next schedule.", flush=True)
                sys.exit(0)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] 🚀 Attempt #{attempt}: Requesting VM creation...", end=" ", flush=True)

        try:
            response = compute_client.launch_instance(launch_details)
            instance = response.data
            print("\n\n" + "🎉" * 20, flush=True)
            print(f"✅ SUCCESS! VM INSTANCE CREATED SUCCESSFULLY!", flush=True)
            print("🎉" * 20, flush=True)
            print(f"   Instance ID:   {instance.id}", flush=True)
            print(f"   Display Name:  {instance.display_name}", flush=True)
            print(f"   Current State: {instance.lifecycle_state}", flush=True)
            print("=" * 60, flush=True)

            play_success_sound()

            public_ip = get_instance_public_ip(compute_client, network_client, compartment_id, instance.id)

            ssh_user = "ubuntu" if "ubuntu" in image_name.lower() else "opc"
            ssh_cmd = f"ssh -i {SSH_KEY_NAME} {ssh_user}@{public_ip}" if public_ip else "N/A"

            # Read private key content for notification
            priv_key_content = ""
            if os.path.exists(SSH_KEY_NAME):
                with open(SSH_KEY_NAME, "r", encoding="utf-8") as f:
                    priv_key_content = f.read().strip()

            # Save details to file
            details_content = f"""OCI Free Tier VM Created Successfully!
======================================
Date: {now_str}
Instance ID: {instance.id}
Shape: VM.Standard.A1.Flex ({OCPUS} OCPU, {MEMORY_IN_GBS} GB RAM)
Public IP: {public_ip}
SSH Command: {ssh_cmd}
SSH Private Key Path: {os.path.abspath(SSH_KEY_NAME)}
"""
            with open("instance_created.txt", "w", encoding="utf-8") as f:
                f.write(details_content)

            print("\n" + details_content, flush=True)
            print(f"💾 Details saved to 'instance_created.txt'.", flush=True)

            # Send Telegram alert if configured
            tg_msg = (
                f"🎉 *Oracle Free 12GB VM Created!* 🎉\n\n"
                f"📍 *Region:* ap-mumbai-1\n"
                f"💻 *Shape:* VM.Standard.A1.Flex (2 OCPU, 12 GB RAM)\n"
                f"🌐 *Public IP:* `{public_ip}`\n"
                f"🔑 *SSH Command:*\n`{ssh_cmd}`\n\n"
                f"🔐 *SSH Private Key:*\n```\n{priv_key_content}\n```"
            )
            send_telegram_alert(tg_msg)
            break

        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in str(e.message) or e.status == 500:
                print(f"⏳ Out of capacity in Mumbai. Retrying in {RETRY_INTERVAL}s...", flush=True)
            elif e.status == 429:
                print(f"⚠️ Rate limited (429). Backing off for {RETRY_INTERVAL + 30}s...", flush=True)
                time.sleep(30)
            elif "LimitExceeded" in str(e.code):
                print(f"\n❌ Error: Limit exceeded! {e.message}", flush=True)
                print("તમારું એકાઉન્ટ લિમિટ ચેક કરો (કદાચ પહેલાથી કોઈ બીજી instance બનેલી છે).", flush=True)
                send_telegram_alert(f"❌ OCI Error: Limit Exceeded - {e.message}")
                break
            else:
                print(f"\n⚠️ OCI Service Error [{e.status} - {e.code}]: {e.message}", flush=True)
                print(f"   Retrying in {RETRY_INTERVAL}s...", flush=True)
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"\n⚠️ Unexpected error: {e}", flush=True)
            print(f"   Retrying in {RETRY_INTERVAL}s...", flush=True)

        attempt += 1
        time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()
