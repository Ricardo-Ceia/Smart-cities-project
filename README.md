# SoundDash - Instalação Local com Simulação de Estação de Monitorização Sonora

Este tutorial descreve o processo de instalação do ambiente SoundDash numa máquina virtual com o sistema operativo Raspberry Pi Desktop. O objetivo é simular uma estação de monitorização de som em ambiente local para testes e desenvolvimento.

## 🧰 Requisitos

- [VirtualBox](https://www.virtualbox.org) — Instalar a versão compatível com o seu sistema operativo.
- [Imagem do Raspberry Pi Desktop](https://www.raspberrypi.com/software/raspberry-pi-desktop)

---

## 🖥️ 1. Preparar a Máquina Virtual

1. Instalar o VirtualBox.
2. Descarregar a imagem do Raspberry Pi Desktop.
3. Criar uma nova máquina virtual no VirtualBox:
   - Utilizar a imagem descarregada como disco de arranque.
   - Durante a instalação do sistema operativo:
     - Quando for apresentada a opção **"Write the changes to disks"**, selecionar **Yes**.
     - Instalar o **GRUB boot loader** quando solicitado.

4. Concluir a instalação:
   - Criar o utilizador.
   - Definir as preferências regionais.

---

## 🐳 2. Instalar Docker e Docker Compose

Abrir o terminal e executar os seguintes comandos:

```bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install docker docker-compose
```

---

## 📦 3. Criar os Serviços com Docker

### 3.1 Node-RED

```bash
sudo docker run -it -p 1880:1880 -v node_red_data:/data --name mynodered nodered/node-red:1.2.0-10-arm32v6
```

- A interface ficará disponível em: [http://127.0.0.1:1880](http://127.0.0.1:1880)

---

### 3.2 Mosquitto (Broker MQTT)

1. Criar um ficheiro `mosquitto.conf` com o seguinte conteúdo:

```conf
bind_address 0.0.0.0
port 1883
allow_anonymous true
```

2. Iniciar o contentor (substituir `<path>` pelo caminho absoluto para o ficheiro):

```bash
sudo docker run --name mosquitto -it -p 1883:1883 -p 9001:9001 -v <path>/mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto
```

---

### 3.3 Grafana

1. Criar um ficheiro `custom.ini` com o seguinte conteúdo:

```ini
[security]
allow_embedding = true

[auth.anonymous]
enabled = true
```

2. Iniciar o contentor (substituir `<path>` pelo caminho absoluto para o ficheiro):

```bash
sudo docker run --platform linux/arm/v7 --mount type=bind,source=<path>,target=/etc/grafana/grafana.ini -d -p 3000:3000 --name=grafana grafana/grafana-oss
```

- A interface ficará disponível em: [http://localhost:3000](http://localhost:3000)

---

## ☁️ 4. Configurar o InfluxDB Cloud

1. Criar uma conta gratuita na [InfluxDB Cloud Serverless](https://cloud2.influxdata.com/).
2. Criar um bucket (base de dados) para armazenar os dados sonoros.
3. Guardar os seguintes dados para integração com os serviços:
   - URL da instância
   - Organization ID
   - Token de autenticação
   - Nome do bucket

---
