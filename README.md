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
```

---

## Setup

### Clone Repository

Clone repository ini dengan kode berikut.
```bash
git clone https://github.com/iskandarmrp/ev-motorbike-scheduling.git
```

### Setup Open Source Routing Machine

1. Download OpenStreetMap data untuk Pulau Jawa pada https://download.geofabrik.de/asia/indonesia.html, Download file java-latest.osm.pbf.
2. Buat folder baru bernama 'osrm' di root directory.
3. Taruh file java-latest.osm.pbf di dalam folder tersebut.
4. Aktifkan docker.
5. Buka terminal di root directory.
6. Jalankan kode berikut.
```bash
docker run -t -v %cd%/osrm:/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/java-latest.osm.pbf
```
```bash
docker run -t -v %cd%/osrm:/data osrm/osrm-backend osrm-contract /data/java-latest.osrm
```

### Setup Virtual Environment

1. Buka terminal di root directory.
2. Buat virtual environment dengan kode berikut.
```bash
python -m venv .venv
```
3. Aktifkan virtual environment dengan kode berikut.
```bash
.venv\Scripts\activate
``` 
4. Install seluruh library pada requirements.txt di dalam virtual environment dengan kode berikut.
```bash
pip install -r requirements.txt
```

### Setup untuk Frontend

1. Buka terminal di root directory.
2. Pindah ke frontend directory dengan kode berikut.
```bash
cd frontend
```
3. Install dependensi dengan kode berikut.
```bash
npm install
```
4. Build dengan kode berikut.
``` bash
npm run build
```

---

## Simulasi

### Simulasi Tanpa Menggunakan Sistem

1. Aktifkan docker.
2. Buka terminal 1 di root directory.
3. Aktifkan OSRM dengan kode berikut pada terminal 1.
```bash
docker run -t -i -p 5000:5000 -v %cd%/osrm:/data osrm/osrm-backend osrm-routed --algorithm ch /data/java-latest.osrm
```
4. Buka terminal 2 di root directory.
5. Aktifkan virtual environment pada terminal 2.
6. Pindah ke simulasi tanpa menggunakan sistem directory dengan kode berikut pada terminal 2.
```bash
cd simulation_testing/no_schedule
```
7. Jalankan simulasi dengan kode berikut pada terminal 2.
```bash
python simulation.py
```
8. Masukkan input berupa jumlah pengemudi dan jumlah stasiun penukaran baterai yang ingin disimulasikan pada terminal 2.
9. Simulasi akan berjalan selama 3 kali, tunggu simulasi sampai selesai.
10. Hasil dari simulasi berupa beberapa grafik yang akan tersimpan dan dapat dilihat pada folder yang sama dengan simulation.py yang dijalankan.
11. Setelah proses selesai, matikan semua terminal.
12. Ulangi langkah-langkah sebelumnya untuk melakukan simulasi dengan skenario yang berbeda.

### Simulasi dengan Menggunakan Sistem

1. Aktifkan docker.
2. Buka terminal 1 di root directory.
3. Aktifkan OSRM dengan kode berikut pada terminal 1.
```bash
docker run -t -i -p 5000:5000 -v %cd%/osrm:/data osrm/osrm-backend osrm-routed --algorithm ch /data/java-latest.osrm
```
4. Buka terminal 2 di root directory.
5. Aktifkan virtual environment pada terminal 2.
6. Aktifkan backend dengan kode berikut pada terminal 2.
```bash
docker compose up --build
```
7. Buka terminal 3 di root directory.
8. Aktifkan virtual environment pada terminal 3.
9. Pindah ke simulasi dengan menggunakan sistem directory dengan kode berikut pada terminal 3.
```bash
cd simulation_testing/using_schedule
```
10. Jalankan simulasi dengan kode berikut pada terminal 3.
```bash
python simulation.py
```
11. Masukkan input berupa jumlah pengemudi dan jumlah stasiun penukaran baterai yang ingin disimulasikan pada terminal 3.
12. Buka terminal 4 di root directory.
13. Pindah ke frontend directory dengan kode berikut pada terminal 4.
```bash
cd frontend
```
14. Jalankan frontend dengan kode berikut pada terminal 4.
```bash
npm run start
```
15. Website dashboard admin dapat dilihat pada localhost.
16. Masukkan username: admin dan password: admin123 untuk login pada website dashboard admin.
17. Informasi mengenai pengemudi, stasiun penukaran baterai, dan jadwal penukaran dapat terlihat pada website dashboard admin.
18. Simulasi yang berjalan pada terminal 3 akan berjalan selama 3 kali, tunggu simulasi sampai selesai.
19. Hasil dari simulasi berupa beberapa grafik yang akan tersimpan dan dapat dilihat pada folder yang sama dengan simulation.py yang dijalankan.
20. Setelah proses selesai, non-aktifkan backend dan jalankan kode berikut pada terminal 2.
```bash
docker compose down -v
```
21. Matikan semua terminal.
22. Ulangi langkah-langkah sebelumnya untuk melakukan simulasi dengan skenario yang berbeda.

---

Setelah kedua simulasi selesai, hasil dari kedua simulasi dapat dibandingkan untuk mengevaluasi efektivitas dari sistem ini.
