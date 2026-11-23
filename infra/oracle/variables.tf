# ---------------------------------------------------------------------------
# Credenciales de la API de OCI (se obtienen en la consola: Perfil → API keys).
# Van en terraform.tfvars, que NUNCA se sube a git.
# ---------------------------------------------------------------------------
variable "tenancy_ocid" {
  description = "OCID del tenancy (la cuenta de Oracle Cloud)."
  type        = string
}

variable "user_ocid" {
  description = "OCID del usuario dueño de la API key."
  type        = string
}

variable "fingerprint" {
  description = "Huella de la API key (aparece al subir la clave pública)."
  type        = string
}

variable "private_key_path" {
  description = "Ruta a la clave privada PEM de la API key (fuera del repo)."
  type        = string
}

variable "region" {
  description = "Región de OCI. Debe ser tu región HOME: los recursos Always Free solo existen ahí."
  type        = string
}

variable "compartment_ocid" {
  description = "Compartimento donde crear todo. Vacío = el compartimento raíz (tenancy)."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------
variable "ssh_public_key" {
  description = "Tu clave pública SSH (contenido de ~/.ssh/id_ed25519.pub)."
  type        = string
}

variable "admin_cidr" {
  description = "IP desde la que se permite SSH, en formato CIDR (tu IP pública + /32). Nunca 0.0.0.0/0."
  type        = string

  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && var.admin_cidr != "0.0.0.0/0"
    error_message = "admin_cidr debe ser un CIDR válido y no puede abrir SSH a todo internet."
  }
}

# ---------------------------------------------------------------------------
# Servidor (Ampere A1, ARM). Always Free permite en total 4 OCPU y 24 GB de RAM.
# ---------------------------------------------------------------------------
variable "instance_ocpus" {
  description = "Núcleos ARM (Always Free: hasta 4 en total)."
  type        = number
  default     = 2

  validation {
    condition     = var.instance_ocpus >= 1 && var.instance_ocpus <= 4
    error_message = "Entre 1 y 4 OCPU para no salir del plan Always Free."
  }
}

variable "instance_memory_gb" {
  description = "RAM en GB (Always Free: hasta 24 en total)."
  type        = number
  default     = 12

  validation {
    condition     = var.instance_memory_gb >= 6 && var.instance_memory_gb <= 24
    error_message = "Entre 6 y 24 GB para no salir del plan Always Free."
  }
}

variable "boot_volume_gb" {
  description = "Disco en GB (Always Free: 200 GB de almacenamiento en bloque en total)."
  type        = number
  default     = 100

  validation {
    condition     = var.boot_volume_gb >= 50 && var.boot_volume_gb <= 200
    error_message = "Entre 50 y 200 GB."
  }
}

# ---------------------------------------------------------------------------
# Costos
# ---------------------------------------------------------------------------
variable "budget_alert_email" {
  description = "Correo que recibe la alerta si la cuenta llega a gastar 1 USD (red de seguridad)."
  type        = string
}

variable "project" {
  description = "Prefijo de nombres y etiqueta de todos los recursos."
  type        = string
  default     = "panastatus"
}
