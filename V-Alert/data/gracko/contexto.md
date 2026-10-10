# Contexto — gracko

- **Giro:** despacho contable y fiscal (nomina, declaraciones y cierres mensuales de clientes).
- **Empleados:** 12, en una sola oficina.
- **Horario:** lunes a viernes 08:00–18:00; sabados 09:00–13:00.

## Sistemas criticos

| Sistema | Descripcion | Ventana critica |
|---|---|---|
| fs-01 (Windows Server 2019) | Servidor de archivos; volumen `/data` con expedientes de clientes | Todo el horario |
| ERP contable (web) | Captura de polizas, nomina y cierres; corre en fs-01 | Cierre mensual (dias 1-5) |
| fw-01 (firewall perimetral) | Acceso a internet, VPN para socio y contador externo | Todo el horario |
| Respaldo nocturno | Copia de /data a NAS, 23:00 | Diario |

## Eventos de negocio

- **Viernes 9 de octubre:** carga masiva de declaraciones del cliente de mayor volumen (17:00–19:30).
- **Lunes 12 de octubre:** cierre de nomina quincenal, 10:00–14:00 (carga alta en el ERP).

## Notas
- Telemetria: CPU, RAM, disco de /data, latencia del ERP y errores por minuto.
- Riesgo conocido: /data sin alerta de capacidad desde hace 3 meses.
