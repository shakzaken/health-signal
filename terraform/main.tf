terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.49"
    }
  }
  required_version = ">= 1.6"
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH key uploaded to Hetzner so we can access the server
resource "hcloud_ssh_key" "default" {
  name       = "health-signal"
  public_key = var.ssh_public_key
}

# Firewall — allow SSH, HTTP, HTTPS only
resource "hcloud_firewall" "default" {
  name = "health-signal"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# CX33 — x86, 4 vCPU, 8 GB RAM, 80 GB SSD, Nuremberg (Germany)
resource "hcloud_server" "main" {
  name        = "health-signal"
  server_type = "cx33"
  image       = "ubuntu-24.04"
  location    = "nbg1"
  ssh_keys    = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.default.id]

  # Install Docker on first boot
  user_data = <<-EOT
    #!/bin/bash
    apt-get update -y
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable docker
    systemctl start docker
  EOT
}

# Floating IP — static IP address for DNS
resource "hcloud_floating_ip" "main" {
  type      = "ipv4"
  home_location = "nbg1"
  name      = "health-signal"
}

# Attach floating IP to server
resource "hcloud_floating_ip_assignment" "main" {
  floating_ip_id = hcloud_floating_ip.main.id
  server_id      = hcloud_server.main.id
}
