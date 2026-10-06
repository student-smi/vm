import os
import sys
import time
import datetime
import subprocess
import configparser
import base64

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
INSTANCE_NAME_PREFIX = "Free-AI-Server"
BOOT_VOLUME_GB = 50       # 50 GB Boot Volume (Always Free up to 200 GB)
RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", "60"))  # Seconds between attempts
OS_PREFERENCE = "Ubuntu"  # "Ubuntu" or "Oracle-Linux"

# Run limit in minutes (useful for GitHub Actions to prevent sudden runner kills)
MAX_RUN_MINUTES = int(os.environ.get("MAX_RUN_MINUTES", "0"))  # 0 means infinite loop

# Multi-Tier Fallback Candidates (All ARM Ampere Always Free)
CANDIDATE_CONFIGS = [
    {
        "name": "ARM-12GB (2 OCPU / 12 GB RAM)",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 2,
        "memory_in_gbs": 12,
        "is_flex": True,
        "arch": "aarch64",
    },
    {
        "name": "ARM-8GB (2 OCPU / 8 GB RAM)",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 2,
        "memory_in_gbs": 8,
        "is_flex": True,
        "arch": "aarch64",
    },
    {
        "name": "ARM-6GB (1 OCPU / 6 GB RAM)",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 1,
        "memory_in_gbs": 6,
        "is_flex": True,
        "arch": "aarch64",
    },
    {
        "name": "ARM-4GB (1 OCPU / 4 GB RAM)",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 1,
        "memory_in_gbs": 4,
        "is_flex": True,
        "arch": "aarch64",
    },
    {
        "name": "ARM-2GB (1 OCPU / 2 GB RAM)",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 1,
        "memory_in_gbs": 2,
        "is_flex": True,
        "arch": "aarch64",
    },
]


def print_banner():
    banner = r"""
============================================================
   🚀 OCI Always Free Multi-Tier VM Auto-Launcher 🚀
============================================================
 Multi-Size Fallback: 12GB -> 8GB -> 6GB -> 4GB -> 2GB -> 1GB
 Region: ap-mumbai-1 | OS: Ubuntu 24.04
 Ready for: OmniRoute + Claude Code + RuFlow
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
            "key_file": key_file_path
        }
    elif os.path.exists(CONFIG_FILE):
        print(f"⚙️ Loading configuration from {CONFIG_FILE}...")
        parser = configparser.ConfigParser()
        parser.read(CONFIG_FILE)
        section = "DEFAULT" if "DEFAULT" in parser else parser.sections()[0]
        config = dict(parser[section])
        if "key_file" in config and not os.path.isabs(config["key_file"]):
            base_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
            config["key_file"] = os.path.join(base_dir, config["key_file"])
    else:
        print(f"[ERROR] Neither GitHub Action environment variables nor '{CONFIG_FILE}' were found.")
        return None, None

    # Load or generate SSH key for connecting to the VM
    pub_key_path = f"{SSH_KEY_NAME}.pub"
    priv_key_path = SSH_KEY_NAME

    if not os.path.exists(pub_key_path) or not os.path.exists(priv_key_path):
        print("🔑 SSH key pair not found. Generating new ed25519 SSH key pair...")
        try:
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", SSH_KEY_NAME, "-N", "", "-C", "oci-vm-user"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ Created SSH keys: {priv_key_path} and {pub_key_path}")
        except Exception as e:
            print(f"⚠️ Could not generate ed25519 key: {e}. Trying rsa 2048...")
            subprocess.run(
                ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", SSH_KEY_NAME, "-N", "", "-C", "oci-vm-user"],
                check=True
            )

    with open(pub_key_path, "r", encoding="utf-8") as f:
        ssh_pub_key = f.read().strip()

    return config, ssh_pub_key


def get_oci_clients(config):
    oci.config.validate_config(config)
    identity_client = oci.identity.IdentityClient(config)
    compute_client = oci.core.ComputeClient(config)
    network_client = oci.core.VirtualNetworkClient(config)
    return identity_client, compute_client, network_client


def get_availability_domain(identity_client, compartment_id):
    ads = identity_client.list_availability_domains(compartment_id).data
    if not ads:
        raise RuntimeError("No Availability Domains found in compartment.")
    return ads[0].name


def find_or_create_network(network_client, compartment_id):
    """Find existing public subnet or create one automatically."""
    print("🌐 Checking virtual cloud network (VCN) and subnets...")
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


def get_image_for_shape(compute_client, compartment_id, shape, arch, os_name="Ubuntu"):
    """Find the latest compatible image for the given shape and architecture."""
    images = compute_client.list_images(
        compartment_id=compartment_id,
        shape=shape,
        sort_by="TIMECREATED",
        sort_order="DESC"
    ).data

    chosen = None
    for img in images:
        name = img.display_name.lower()
        if os_name.lower() in name:
            if arch == "aarch64" and "aarch64" in name:
                chosen = img
                break
            elif arch == "x86_64" and "aarch64" not in name:
                chosen = img
                break

    if not chosen and images:
        chosen = images[0]

    if not chosen:
        raise RuntimeError(f"No compatible {arch} image found for shape {shape}")

    return chosen.id, chosen.display_name


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


def get_cloud_init_userdata():
    """Generates cloud-init base64 script to configure 4GB swap space on boot."""
    script = """#!/bin/bash
# Auto-configure 4GB swap space so low RAM instances never run out of memory
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.conf
"""
    return base64.b64encode(script.encode("utf-8")).decode("utf-8")


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
    except Exception as e:
        print(f"❌ Error during resource lookup: {e}")
        return

    # Pre-cache image IDs for each shape
    image_cache = {}
    for candidate in CANDIDATE_CONFIGS:
        key = (candidate["shape"], candidate["arch"])
        if key not in image_cache:
            try:
                img_id, img_name = get_image_for_shape(compute_client, compartment_id, candidate["shape"], candidate["arch"], OS_PREFERENCE)
                image_cache[key] = (img_id, img_name)
                print(f"   🔍 Cached image for {candidate['shape']} ({candidate['arch']}): {img_name}")
            except Exception as e:
                print(f"   ⚠️ Could not find image for {candidate['shape']}: {e}")

    userdata_b64 = get_cloud_init_userdata()

    print("\n" + "=" * 60)
    print("📋 MULTI-TIER FALLBACK STRATEGY ACTIVE:")
    for idx, c in enumerate(CANDIDATE_CONFIGS, 1):
        print(f"   Tier {idx}: {c['name']}")
    print(f"   - Boot Volume:    {BOOT_VOLUME_GB} GB (Auto 4GB Swap enabled)")
    print(f"   - Availability AD: {ad}")
    print(f"   - Retry Interval: {RETRY_INTERVAL} seconds")
    if MAX_RUN_MINUTES > 0:
        print(f"   - Max Run Time:   {MAX_RUN_MINUTES} minutes")
    print("=" * 60)
    print("🔄 Starting retry loop. Script will test each tier in order until capacity is secured...")
    print("   (Press Ctrl + C anytime to stop)\n", flush=True)

    start_time = time.time()
    attempt = 1

    while True:
        if MAX_RUN_MINUTES > 0:
            elapsed_minutes = (time.time() - start_time) / 60.0
            if elapsed_minutes >= MAX_RUN_MINUTES:
                print(f"\n⏱️ Reached max run limit of {MAX_RUN_MINUTES}m. Ending this run cleanly for next schedule.", flush=True)
                sys.exit(0)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now_str}] 🚀 Attempt #{attempt}:", flush=True)

        for candidate in CANDIDATE_CONFIGS:
            shape_key = (candidate["shape"], candidate["arch"])
            if shape_key not in image_cache:
                continue

            image_id, image_name = image_cache[shape_key]
            candidate_name = candidate["name"]
            inst_display_name = f"{INSTANCE_NAME_PREFIX}-{candidate['ocpus']}c-{candidate['memory_in_gbs']}g"

            shape_config = None
            if candidate["is_flex"]:
                shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=float(candidate["ocpus"]),
                    memory_in_gbs=float(candidate["memory_in_gbs"])
                )

            launch_details = oci.core.models.LaunchInstanceDetails(
                compartment_id=compartment_id,
                availability_domain=ad,
                shape=candidate["shape"],
                shape_config=shape_config,
                display_name=inst_display_name,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id,
                    boot_volume_size_in_gbs=BOOT_VOLUME_GB
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet_id,
                    assign_public_ip=True,
                    display_name=f"{inst_display_name}-vnic"
                ),
                metadata={
                    "ssh_authorized_keys": ssh_pub_key,
                    "user_data": userdata_b64
                }
            )

            print(f"   ▶ Trying {candidate_name}...", end=" ", flush=True)

            try:
                response = compute_client.launch_instance(launch_details)
                instance = response.data

                print("\n\n" + "🎉" * 20, flush=True)
                print(f"✅ SUCCESS! VM INSTANCE ALLOCATED SUCCESSFULLY!", flush=True)
                print(f"   Allocated:     {candidate_name}", flush=True)
                print("🎉" * 20, flush=True)
                print(f"   Instance ID:   {instance.id}", flush=True)
                print(f"   Display Name:  {instance.display_name}", flush=True)
                print(f"   Current State: {instance.lifecycle_state}", flush=True)
                print("=" * 60, flush=True)

                play_success_sound()

                public_ip = get_instance_public_ip(compute_client, network_client, compartment_id, instance.id)
                ssh_user = "ubuntu" if "ubuntu" in image_name.lower() else "opc"
                ssh_cmd = f"ssh -i {SSH_KEY_NAME} {ssh_user}@{public_ip}" if public_ip else "N/A"

                priv_key_content = ""
                if os.path.exists(SSH_KEY_NAME):
                    with open(SSH_KEY_NAME, "r", encoding="utf-8") as f:
                        priv_key_content = f.read().strip()

                details_content = f"""OCI Free Tier VM Created Successfully!
======================================
Date: {now_str}
Allocated Tier: {candidate_name}
Instance ID: {instance.id}
Shape: {candidate['shape']} ({candidate['ocpus']} OCPU, {candidate['memory_in_gbs']} GB RAM)
Public IP: {public_ip}
SSH Command: {ssh_cmd}
SSH Private Key Path: {os.path.abspath(SSH_KEY_NAME)}
"""
                with open("instance_created.txt", "w", encoding="utf-8") as f:
                    f.write(details_content)

                print("\n" + details_content, flush=True)
                print(f"💾 Details saved to 'instance_created.txt'.", flush=True)

                tg_msg = (
                    f"🎉 *Oracle Free VM Created!* 🎉\n\n"
                    f"📍 *Region:* ap-mumbai-1\n"
                    f"💻 *Allocated Tier:* {candidate_name}\n"
                    f"🌐 *Public IP:* `{public_ip}`\n"
                    f"🔑 *SSH Command:*\n`{ssh_cmd}`\n\n"
                    f"🔐 *SSH Private Key:*\n```\n{priv_key_content}\n```"
                )
                send_telegram_alert(tg_msg)
                return

            except oci.exceptions.ServiceError as e:
                is_capacity_issue = (
                    "Out of host capacity" in str(e.message)
                    or "Invalid ratio of memory" in str(e.message)
                    or "Valid ratio range: 0 - 0" in str(e.message)
                    or e.status == 500
                )
                if is_capacity_issue:
                    print("⏳ Capacity currently full in Mumbai.", flush=True)
                elif e.status == 429:
                    print("⚠️ Rate limit (429).", flush=True)
                    time.sleep(15)
                elif "LimitExceeded" in str(e.code):
                    print(f"\n❌ Error: Limit exceeded! {e.message}", flush=True)
                    send_telegram_alert(f"❌ OCI Error: Limit Exceeded - {e.message}")
                    return
                else:
                    print(f"⚠️ Error [{e.status}]: {e.message}", flush=True)
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user.", flush=True)
                return
            except Exception as e:
                print(f"⚠️ Unexpected error: {e}", flush=True)

        attempt += 1
        print(f"⏳ Waiting {RETRY_INTERVAL}s before next round of checks...", flush=True)
        time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()
