# Oracle Cloud A1.Flex Deployment Guide

This guide provides step-by-step instructions for deploying JARVIS on Oracle Cloud's Ampere A1.Flex Always Free VM (4 OCPU, 24GB RAM, Oracle Linux 9).

## 1. VM Creation
1. Log into your Oracle Cloud Console.
2. Navigate to **Compute > Instances** and click **Create Instance**.
3. **Image and Shape:** 
   - Leave Image as **Oracle Linux 9**.
   - Change Shape to **Ampere A1.Flex** (Virtual Machine).
   - Configure it for **4 OCPUs** and **24 GB RAM**. (This is within the Always Free tier limits).
4. **Networking:** Ensure you assign a public IPv4 address.
5. **SSH Keys:** Save the generated SSH private key to your local machine (e.g., `oracle-key.key`).
6. Click **Create**.

## 2. Oracle Security List Configuration
You must open ports 8000 (for JARVIS) and 8001 (for the GitHub webhook) in the Oracle Cloud Console.
1. Go to your Instance details page.
2. Click on the attached **Subnet**, then click on the **Default Security List**.
3. Add an **Ingress Rule**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `8000,8001`
   - **Description:** JARVIS Backend and Webhook

## 3. Connect via SSH
Use the private key you downloaded to connect to your instance. For Oracle Linux, the default username is `opc`.
```bash
# On your local machine:
chmod 400 oracle-key.key
ssh -i oracle-key.key opc@<YOUR_ORACLE_VM_IP>
```

## 4. Run the Setup Script
Once connected, fetch and run the setup script:
```bash
wget https://raw.githubusercontent.com/username/Jarvis/main/deploy/oracle_setup.sh
chmod +x oracle_setup.sh
./oracle_setup.sh
```
*Note: The script will prompt you for your Git repository URL.*

## 5. Configure the Firewall (firewalld)
Oracle Linux uses `firewalld` which by default blocks most ports. You must explicitly open them on the VM:
```bash
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
sudo firewall-cmd --zone=public --add-port=8001/tcp --permanent
sudo firewall-cmd --reload
```

## 6. Transfer Credentials (SCP)
Unlike Render, Oracle VMs have persistent disk storage. You **do not** need to rely on base64 environment variables for your Google credentials.
From your **local machine**, securely copy your credential files directly into the JARVIS folder on the VM:

```bash
# Transfer main credentials
scp -i oracle-key.key path/to/credentials.json opc@<YOUR_ORACLE_VM_IP>:/home/opc/Jarvis/credentials.json

# Transfer database token (create database folder if it doesn't exist)
ssh -i oracle-key.key opc@<YOUR_ORACLE_VM_IP> "mkdir -p /home/opc/Jarvis/database"
scp -i oracle-key.key path/to/database/google_token.json opc@<YOUR_ORACLE_VM_IP>:/home/opc/Jarvis/database/google_token.json

# Transfer your .env file
scp -i oracle-key.key path/to/.env opc@<YOUR_ORACLE_VM_IP>:/home/opc/Jarvis/.env
```

## 7. Start JARVIS via PM2
Inside the `/home/opc/Jarvis` folder, start the application using PM2 to keep it running continuously in the background.

```bash
cd /home/opc/Jarvis
pm2 start deploy/oracle_start.sh --name "jarvis"

# To ensure PM2 starts Jarvis automatically on VM reboot:
pm2 save
pm2 startup
# Run the command that `pm2 startup` prints out.
```

## 8. GitHub Auto-Deploy Webhook (Optional)
If you want JARVIS to automatically pull the latest code from GitHub and restart when you push to the `main` branch:

1. Start the webhook server via PM2:
   ```bash
   # Inside the Jarvis directory
   source venv/bin/activate
   pm2 start "python deploy/oracle_webhook_server.py" --name "jarvis-webhook"
   pm2 save
   ```
2. In your GitHub repository, go to **Settings > Webhooks > Add webhook**.
3. **Payload URL:** `http://<YOUR_ORACLE_VM_IP>:8001/webhook`
4. **Content type:** `application/json`
5. **Secret:** (Optional, but recommended) Set a secret, and add `GITHUB_WEBHOOK_SECRET=your_secret` to your `.env` file on the VM, then restart the webhook.
6. **Trigger:** "Just the push event"
7. Click **Add webhook**.

Whenever you push to the `main` branch, GitHub will hit your VM on port 8001, triggering `git pull origin main` and `pm2 restart jarvis`.
