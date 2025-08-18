# Usar a imagem oficial do MySQL
FROM mysql:8.0

# Definir variáveis de ambiente
ENV MYSQL_ROOT_PASSWORD=root
ENV MYSQL_DATABASE=testdb
ENV MYSQL_USER=testuser
ENV MYSQL_PASSWORD=testpass

# Expor a porta padrão do MySQL
EXPOSE 3306
