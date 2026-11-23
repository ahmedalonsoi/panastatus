output "public_ip" {
  description = "IP pública del servidor: crea con ella el registro DNS A de tu dominio."
  value       = oci_core_instance.server.public_ip
}

output "ssh" {
  description = "Comando para entrar al servidor."
  value       = "ssh deploy@${oci_core_instance.server.public_ip}"
}

output "grafana_tunnel" {
  description = "Túnel SSH para abrir Grafana en http://localhost:3001 (no está expuesto a internet)."
  value       = "ssh -N -L 3001:127.0.0.1:3001 deploy@${oci_core_instance.server.public_ip}"
}
