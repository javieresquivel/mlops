FROM grafana/grafana:latest

ENV GF_SECURITY_ADMIN_PASSWORD=admin

# Comentario de test
COPY ./provisioning /etc/grafana/
COPY ./dashboards /var/lib/grafana/

EXPOSE 3000