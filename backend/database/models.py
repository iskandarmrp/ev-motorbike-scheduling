from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Interval
from sqlalchemy.orm import relationship
from .database import Base

class Admin(Base):
    __tablename__ = "admin"
    username = Column(String, primary_key=True, index=True)
    password = Column(String)
    nama = Column(String)

class Baterai(Base):
    __tablename__ = "baterai"
    id = Column(Integer, primary_key=True)
    kapasitas_maksimum = Column(Float)
    kapasitas_baterai_saat_ini = Column(Float)
    total_baterai_pengecasan = Column(Float)
    siklus_baterai = Column(Float)

class Kendaraan(Base):
    __tablename__ = "kendaraan"
    id = Column(Integer, primary_key=True)
    id_baterai = Column(Integer)
    kecepatan_maksimum = Column(Float)

class Pengemudi(Base):
    __tablename__ = "pengemudi"
    id = Column(Integer, primary_key=True)
    id_kendaraan = Column(Integer)
    status = Column(String)
    online_status = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

class Order(Base):
    __tablename__ = "order"
    id = Column(Integer, primary_key=True)
    status = Column(String)
    waktu_pencarian = Column(Float)
    id_pengemudi = Column(Integer, nullable=True)
    latitude_awal = Column(Float)
    longitude_awal = Column(Float)
    latitude_tujuan = Column(Float)
    longitude_tujuan = Column(Float)
    waktu_dibuat = Column(DateTime)
    waktu_selesai = Column(DateTime, nullable=True)

class StasiunPenukaranBaterai(Base):
    __tablename__ = "stasiun_penukaran_baterai"
    id = Column(Integer, primary_key=True)
    nama_stasiun = Column(String)
    total_slot = Column(Integer)
    alamat = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    slots = relationship("SlotStasiunPenukaranBaterai", back_populates="stasiun", cascade="all, delete-orphan")

class SlotStasiunPenukaranBaterai(Base):
    __tablename__ = "slot_stasiun_penukaran_baterai"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_stasiun_penukaran_baterai = Column(Integer, ForeignKey("stasiun_penukaran_baterai.id"))
    id_baterai = Column(Integer)
    slot_number = Column(Integer)

    stasiun = relationship("StasiunPenukaranBaterai", back_populates="slots")

class JadwalPenukaran(Base):
    __tablename__ = "jadwal_penukaran"
    id = Column(Integer, primary_key=True)
    id_pengemudi = Column(Integer, ForeignKey("pengemudi.id"))
    id_slot_stasiun_penukaran_baterai = Column(Integer, ForeignKey("slot_stasiun_penukaran_baterai.id"))
    waktu_penukaran = Column(DateTime)
    estimasi_waktu_tunggu = Column(Float)
    estimasi_waktu_tempuh = Column(Float)
    estimasi_baterai_tempuh = Column(Float)
    perkiraan_kapasitas_baterai_yang_ditukar = Column(Float)
    perkiraan_kapasitas_baterai_yang_didapat = Column(Float)
    perkiraan_siklus_baterai_yang_didapat = Column(Float)
    status = Column(String)