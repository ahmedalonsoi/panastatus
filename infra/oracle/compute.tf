# Servidor: Ampere A1 (ARM) con Ubuntu 24.04. Las imágenes Docker del proyecto se
# construyen para linux/arm64 en el CI.

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# La imagen oficial más reciente de Ubuntu 24.04 para ARM.
data "oci_core_images" "ubuntu" {
  compartment_id           = local.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "server" {
  compartment_id = local.compartment_id
  # El primer dominio de disponibilidad. Si OCI responde "Out of host capacity" (pasa
  # con Ampere gratis), probar otro índice o reintentar más tarde.
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "${var.project}-server"
  shape               = "VM.Standard.A1.Flex"
  freeform_tags       = local.tags

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "server"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    # cloud-init prepara el servidor en el primer arranque (Docker, firewall, usuario).
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      ssh_public_key = var.ssh_public_key
    }))
  }

  # Sin metadatos legacy (IMDSv1): mitiga robo de credenciales vía SSRF.
  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  lifecycle {
    # Si Canonical publica una imagen nueva, NO recrear el servidor (se perderían los
    # datos). Las actualizaciones de seguridad llegan por unattended-upgrades.
    ignore_changes = [source_details[0].source_id, metadata["user_data"]]
  }
}
