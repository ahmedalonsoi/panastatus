# Versiones fijadas: el mismo código produce la misma infraestructura hoy y en un año.
terraform {
  required_version = ">= 1.10"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 9.14"
    }
  }

  # Estado: por ahora local (terraform.tfstate, ignorado por git y con secretos dentro:
  # guárdalo con respaldo). Para trabajar en equipo se movería a un bucket de Object
  # Storage de OCI con el backend "s3" (compatible). Ver infra/oracle/README.md.
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}
