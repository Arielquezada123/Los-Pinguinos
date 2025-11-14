# 💧 WaterMillimiter - Proyecto IoT (Despliegue "Los Pingüinos")

Este repositorio contiene el código fuente de "WaterMillimiter", una aplicación web completa de IoT (Internet de las Cosas) diseñada para la monitorización y gestión de medidores de agua en tiempo real.

La plataforma permite recibir datos de sensores (dispositivos IoT), procesarlos, almacenarlos y visualizarlos en un dashboard interactivo.

---

## 🏛️ Arquitectura del Sistema

El proyecto utiliza una arquitectura de microservicios orquestada con **Docker Compose**, asegurando la separación de responsabilidades y la escalabilidad.

La arquitectura se compone de los siguientes servicios:

1.  **Broker MQTT (`mosquitto`):** Un broker **Eclipse Mosquitto** que actúa como el servidor central de mensajería. Los dispositivos IoT (medidores de agua) publican sus lecturas en *topics* de este broker.
2.  **Listener (`mqtt_listener`):** Un servicio de Python (un comando de gestión de Django) que utiliza la biblioteca **Paho-MQTT** para suscribirse al broker `mosquitto`. Este servicio escucha constantemente los datos de los sensores, los procesa y los guarda en la base de datos de Django.
3.  **Aplicación Web (`web`):** El servicio principal de la aplicación, construido con **Django**. Se ejecuta sobre un servidor ASGI **Daphne** para soportar comunicación en tiempo real.
4.  **WebSockets (`channels`):** La aplicación utiliza **Django Channels** para gestionar WebSockets. Esto permite que el `mqtt_listener` (o el backend) envíe los datos recibidos a los dashboards de los clientes (navegadores web) instantáneamente, sin necesidad de recargar la página.
5.  **Channel Layer (`redis`):** Una instancia de **Redis** que sirve como *channel layer* para Django Channels, permitiendo la comunicación entre el `mqtt_listener` y el servicio `web`.
6.  **Reverse Proxy (`nginx`):** Un servidor **Nginx** que actúa como reverse proxy. Gestiona las conexiones web (HTTP/HTTPS), sirve los archivos estáticos y estáticos, y dirige el tráfico al servicio `web` (Daphne).

---

## 🛠️ Tecnologías Principales

**Backend y Lógica:**
* **Python 3**
* **Django 4.2+**: Como framework web principal.
* **Django Channels**: Para la funcionalidad de WebSockets.
* **Daphne**: Como el servidor ASGI para Django.

**Mensajería y IoT:**
* **Paho-MQTT**: Cliente MQTT para que Python pueda suscribirse al broker.
* **Eclipse Mosquitto**: El broker MQTT que recibe los datos de los sensores.

**Orquestación y Despliegue:**
* **Docker & Docker Compose**: Para containerizar y orquestar todos los servicios.
* **Nginx**: Como reverse proxy y servidor de archivos estáticos.
* **Redis**: Como backend (channel layer) para Django Channels.
