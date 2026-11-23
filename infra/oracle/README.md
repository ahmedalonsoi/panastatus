# Infraestructura en Oracle Cloud (OpenTofu)

Crea **todo** lo necesario para correr PanaStatus dentro del plan **Always Free** de Oracle Cloud (costo esperado: 0 USD):

| Recurso | Detalle |
|---|---|
| Red (VCN) | `10.0.0.0/16` con una subred pública `10.0.1.0/24` e Internet Gateway |
| Firewall de la nube | 80/443 abiertos; **22 (SSH) solo desde tu IP** (`admin_cidr`) |
| Servidor | Ampere A1 (ARM), Ubuntu 24.04, 2 OCPU / 12 GB / 100 GB (ajustable hasta 4/24/200) |
| Preparación (cloud-init) | Docker + Compose, usuario `deploy` solo con clave SSH, SSH endurecido, fail2ban, parches de seguridad automáticos, rotación de logs |
| Presupuesto | Correo de alerta si la cuenta gasta **1 USD** (detecta errores de costo) |

## Requisitos (una sola vez)

1. **Cuenta de Oracle Cloud** con el plan Free Tier. La región que elijas al registrarte será tu *home region* y no se puede cambiar: los recursos Always Free solo existen ahí. Elige una cercana a Panamá y con capacidad: `us-ashburn-1` (Virginia) es la más grande. Bogotá (`sa-bogota-1`) tiene menos latencia, pero a menudo se queda sin capacidad Ampere gratuita.
2. **OpenTofu** ≥ 1.10: `winget install OpenTofu.Tofu`.
3. **Clave SSH** (si no tienes una): `ssh-keygen -t ed25519`.
4. **API key de OCI**: Consola → tu perfil → *API keys* → *Add API key* → *Generate key pair*. Descarga la clave privada a `C:\Users\<tú>\.oci\` (**fuera del repo**). OCI te muestra el `tenancy_ocid`, el `user_ocid`, el `fingerprint` y la región.

## Uso

```bash
cd infra/oracle
cp terraform.tfvars.example terraform.tfvars   # y complétalo
tofu init
tofu plan      # muestra qué se va a crear, sin crear nada
tofu apply     # crea los recursos (pide confirmación)
```

Al terminar muestra:

- `public_ip`: créale un registro **DNS A** en tu dominio (`@` → esa IP).
- `ssh`: el comando para entrar como `deploy`.
- `grafana_tunnel`: el túnel para ver Grafana en `http://localhost:3001`.

cloud-init tarda entre 3 y 5 minutos tras el primer arranque. Para comprobar que terminó: `ssh deploy@IP 'cloud-init status --wait && docker --version'`.

## Problemas comunes

- **`Out of host capacity`**: Oracle no tiene Ampere gratuitos libres en ese momento. Reintenta más tarde, o cambia el índice del dominio de disponibilidad en `compute.tf` (`availability_domains[1]`).
- **No puedo entrar por SSH**: tu IP cambió (pasa con el internet de casa). Actualiza `admin_cidr` y vuelve a ejecutar `tofu apply`, que solo modifica el firewall.

## Estado de OpenTofu

`terraform.tfstate` se guarda **local** y está en `.gitignore`: contiene IDs y datos sensibles. Haz un respaldo. Para trabajar en equipo, el paso siguiente sería guardarlo en un bucket de Object Storage de OCI (también gratuito) con el backend `s3`.

## Destruir todo

```bash
tofu destroy
```

Borra el servidor **y sus datos**. Antes haz un respaldo de la base de datos (ver `docs/operacion.md`).
