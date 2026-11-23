# Despliegue en producción (paso a paso)

Orden recomendado. Cada paso dice **quién** lo hace: 👤 tú (requiere tu cuenta, tu tarjeta o una decisión) o 🤖 automático.

## 1. 👤 Dominio

Compra el dominio (por ejemplo en Cloudflare Registrar, Namecheap o Porkbun; unos 10–15 USD al año). Activa la **renovación automática** y la **protección de privacidad WHOIS**. El registro DNS se crea en el paso 4, cuando ya tengas la IP.

## 2. 👤 Cuenta de Oracle Cloud

1. Regístrate en Oracle Cloud Free Tier. Pide tarjeta solo para verificar: lo Always Free no se cobra.
2. **Región home**: `us-ashburn-1` es la más segura para conseguir servidores ARM gratuitos. No se puede cambiar después.
3. Crea la API key: tu perfil → *API keys* → *Add API key* → *Generate*. Guarda la clave privada en `C:\Users\<tú>\.oci\` (**fuera** del repositorio).

## 3. 👤🤖 Crear el servidor con OpenTofu

```bash
winget install OpenTofu.Tofu
ssh-keygen -t ed25519                          # si aún no tienes clave SSH
cd infra/oracle
cp terraform.tfvars.example terraform.tfvars   # complétalo (ver comentarios)
tofu init
tofu plan                                      # revisa: VCN, subred, servidor y presupuesto
tofu apply
```

Anota la salida `public_ip`. Si sale `Out of host capacity`, ver `infra/oracle/README.md`.

## 4. 👤 DNS

En tu proveedor de dominio, crea un registro **A**: nombre `@` → la `public_ip`. Opcional: `www` como CNAME a `@`. Comprueba con `nslookup tudominio.com`.

## 5. 👤 Preparar el servidor (una vez)

```bash
ssh deploy@<IP> 'cloud-init status --wait'     # espera a que termine la preparación
ssh deploy@<IP>
cd /opt/panastatus
nano .env     # copia deploy/.env.production.example y complétalo
chmod 600 .env
```

Genera cada contraseña con `python -c "import secrets; print(secrets.token_urlsafe(24))"`.

## 6. 👤 Repositorio en GitHub

1. Crea el repositorio y sube `main`. Revisa antes que `git status` no muestre `.env` ni `terraform.tfvars`.
2. **Settings → Secrets and variables → Actions**:
   - Secretos:
     - `DEPLOY_HOST`: la IP o el dominio.
     - `DEPLOY_SSH_KEY`: una clave SSH **nueva y exclusiva** para el despliegue. Genérala con `ssh-keygen -t ed25519 -f deploy_key -N ""`, agrega `deploy_key.pub` a `~/.ssh/authorized_keys` del usuario `deploy` en el servidor, y guarda el contenido de `deploy_key` como secreto.
     - `DEPLOY_KNOWN_HOSTS`: la salida de `ssh-keyscan -t ed25519 <IP>`.
   - Variables:
     - `DEPLOY_ENABLED` = `true`
     - `PUBLIC_URL` = `https://tudominio.com`
3. **Settings → Environments → New environment** `production` → activa *Required reviewers* (tú). Así cada despliegue espera tu aprobación con un clic.
4. **Settings → Code security**: activa *Dependabot alerts* y *Secret scanning*.

## 7. 🤖 Primer despliegue

Un push a `main` dispara: CI → construcción de imágenes amd64 y arm64 → escaneo Trivy → (tu aprobación) → despliegue por SSH → verificación de `/health` → rollback si algo falla.

También puedes lanzarlo a mano: **Actions → Deploy → Run workflow**.

## 8. 👤 Verificación final

- `https://tudominio.com` carga con candado (Caddy obtiene el certificado solo en el primer arranque; puede tardar 1 minuto).
- `https://tudominio.com/bot/` muestra el correo de contacto correcto.
- Grafana por el túnel: `ssh -N -L 3001:127.0.0.1:3001 deploy@<IP>` → http://localhost:3001.
- Actualiza en el bot de Telegram la descripción y el enlace al dominio (@BotFather → `/setdescription`).
- Prueba de cabeceras: <https://securityheaders.com> y <https://www.ssllabs.com/ssltest/> (debería dar A o A+).

## 9. Lanzamiento público

Anuncia el bot y la página. Activa los post-mortems con IA poniendo `ANTHROPIC_API_KEY` en el `.env` del servidor y ejecuta `docker compose ... up -d` para que la lea.
