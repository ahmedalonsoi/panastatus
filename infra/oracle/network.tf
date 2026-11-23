# Red: una VCN con una subred pública. El firewall de la nube (security list) es la
# primera capa; el servidor además tiene su propio firewall (cloud-init.yaml).
#
#   internet ──► Internet Gateway ──► subred pública 10.0.1.0/24 ──► servidor
#                                     (abierto: 80, 443 a todos; 22 solo a tu IP)

locals {
  compartment_id = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
  tags           = { project = var.project, managed-by = "opentofu" }
}

resource "oci_core_vcn" "main" {
  compartment_id = local.compartment_id
  display_name   = "${var.project}-vcn"
  cidr_blocks    = ["10.0.0.0/16"]
  dns_label      = var.project
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "main" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-igw"
  enabled        = true
  freeform_tags  = local.tags
}

resource "oci_core_route_table" "public" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-public-rt"
  freeform_tags  = local.tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-public-sl"
  freeform_tags  = local.tags

  # Salida: todo permitido (el checker necesita llegar a cualquier sitio web).
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  # SSH solo desde tu IP.
  ingress_security_rules {
    description = "SSH (solo administrador)"
    source      = var.admin_cidr
    protocol    = "6" # TCP
    tcp_options {
      min = 22
      max = 22
    }
  }

  # HTTP: Caddy lo usa para el reto de Let's Encrypt y para redirigir a HTTPS.
  ingress_security_rules {
    description = "HTTP"
    source      = "0.0.0.0/0"
    protocol    = "6"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    description = "HTTPS"
    source      = "0.0.0.0/0"
    protocol    = "6"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # HTTP/3 (QUIC) va por UDP 443; Caddy lo soporta.
  ingress_security_rules {
    description = "HTTP/3"
    source      = "0.0.0.0/0"
    protocol    = "17" # UDP
    udp_options {
      min = 443
      max = 443
    }
  }

  # ICMP "fragmentation needed": necesario para que Path MTU Discovery funcione.
  ingress_security_rules {
    description = "ICMP path MTU"
    source      = "0.0.0.0/0"
    protocol    = "1"
    icmp_options {
      type = 3
      code = 4
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = local.compartment_id
  vcn_id            = oci_core_vcn.main.id
  display_name      = "${var.project}-public"
  cidr_block        = "10.0.1.0/24"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.public.id]
  freeform_tags     = local.tags
}
