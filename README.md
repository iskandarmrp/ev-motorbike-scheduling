# Sistem Penjadwalan Penukaran Baterai pada Pengemudi Ojek Online

## Overview

Sistem ini bertujuan untuk meningkatkan keuntungan operasional pengemudi ojek online berbasis sepeda motor listrik dengan merancang sistem penjadwalan penukaran baterai secara otomatis. Sistem ini menggunakan algoritma **Adaptive Large Neighborhood Search (ALNS)** untuk mengoptimalkan penjadwalan berdasarkan kondisi lingkungan operasional.

Terdapat dua jenis simulasi:
- **Simulasi tanpa menggunakan sistem**
- **Simulasi menggunakan sistem**

Perbandingan hasil dari kedua simulasi digunakan untuk mengevaluasi efektivitas sistem.

---

## Python Version
```bash
Python 3.11.4

---

## Setup

### Setup Open Source Routing Machine

1. Download OpenStreetMap data untuk Pulau Jawa pada https://download.geofabrik.de/asia/indonesia.html, Download file java-latest.osm.pbf.
2. Buat folder baru bernama 'osrm' di root directory.
3. Taruh file java-latest.osm.pbf di dalam folder tersebut.
4. Aktifkan docker.
5. Buka terminal di root directory.
6. Jalankan kode berikut.
```bash
docker run -t -v %cd%/osrm:/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/java-latest.osm.pbf
```bash
docker run -t -v %cd%/osrm:/data osrm/osrm-backend osrm-contract /data/java-latest.osrm

### Setup Virtual Environment

1. Buka terminal di root directory.
2. Buat virtual environment.
3. Aktifkan virtual environment.
4. Install seluruh library pada requirements.txt.

### Setup untuk Frontend

1. Buka terminal di root directory.
2. Pindah ke frontend directory dengan kode berikut.
```bash
cd frontend
3. Install dependensi dengan kode berikut.
```bash
npm install
4. Build dengan kode berikut.
``` bash
npm run build
