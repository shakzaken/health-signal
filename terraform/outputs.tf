output "server_ip" {
  description = "Main server IP (ephemeral — use floating_ip for DNS)"
  value       = hcloud_server.main.ipv4_address
}

output "floating_ip" {
  description = "Static floating IP — point your DNS A record here"
  value       = hcloud_floating_ip.main.ip_address
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh root@${hcloud_floating_ip.main.ip_address}"
}
