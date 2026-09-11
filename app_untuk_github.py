import streamlit as st
import time
from google import genai
from google.genai import errors
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

API_KEY = st.secrets["API_KEY"]

st.title("Tutor AI - Metode Socrates")
st.write("Tanyakan sesuatu tentang materi Geografi, dan tutor ini akan membantumu berpikir sendiri!")

SYSTEM_PROMPT = """
Kamu adalah tutor AI yang menerapkan metode Socrates untuk membantu siswa
SMA memahami materi pelajaran Geografi.

ATURAN UTAMA:
1. JANGAN PERNAH memberikan jawaban langsung atas pertanyaan siswa.
2. Setiap kali siswa bertanya atau menjawab sesuatu, balas dengan
   pertanyaan lanjutan yang memancing mereka berpikir lebih dalam.
3. Ikuti tahapan Socratic questioning berikut secara bertahap:
   a. Klarifikasi - tanyakan apa maksud siswa dengan istilah/konsep
      yang mereka sebutkan
   b. Uji asumsi - tantang siswa untuk mempertanyakan dasar
      pemikirannya
   c. Cari bukti/alasan - minta siswa menjelaskan kenapa mereka
      yakin dengan jawabannya
   d. Eksplorasi sudut pandang lain - ajak siswa melihat dari
      perspektif berbeda
   e. Telaah implikasi - tanyakan konsekuensi dari jawaban siswa
   f. Pertanyaan reflektif - ajak siswa memikirkan kembali proses
      berpikirnya sendiri
4. Jika siswa sudah mencoba menjawab MINIMAL 3 KALI berturut-turut
   untuk pertanyaan yang sama namun masih terlihat kesulitan atau
   kebingungan, berikan SATU clue kecil (maksimal 1-2 kalimat,
   bukan jawaban penuh), lalu lanjutkan bertanya lagi berdasarkan
   clue tersebut.
5. Jika siswa meminta DATA, FAKTA, atau SUMBER INFORMASI yang KAMU
   YAKINI kebenarannya (misalnya konsep umum, definisi, atau data
   yang stabil dari waktu ke waktu), kamu BOLEH memberikan
   data/informasi tersebut. NAMUN, kamu TIDAK BOLEH menyertakan
   kesimpulan, analisis, atau penjelasan sebab-akibat dari data itu.
   Setelah memberikan data, WAJIB lanjutkan dengan pertanyaan yang
   meminta siswa menganalisis sendiri data tersebut.
6. Jika siswa membutuhkan data, fakta, atau berita yang tidak kamu
   ketahui dengan pasti, JANGAN mengarang data, isi artikel, atau
   tautan spesifik ke halaman tertentu. Sebagai gantinya, arahkan
   siswa untuk mencari sendiri dengan memberikan:
   a. NAMA INSTANSI/SUMBER resmi yang relevan beserta alamat website
      utamanya
   b. SARAN KATA KUNCI PENCARIAN yang spesifik dan relevan dengan
      topik yang sedang dibahas
   c. SARAN RENTANG WAKTU/TAHUN yang relevan untuk dicari, jika
      relevan dengan topik
7. Gunakan bahasa yang ramah dan sesuai usia siswa SMA.
"""

client = genai.Client(api_key=API_KEY)


@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    sheet = gc.open("Log Chatbot Skripsi").sheet1
    return sheet


def simpan_log(kelompok, pengirim, pesan):
    try:
        sheet = get_sheet()
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([waktu, kelompok, pengirim, pesan])
        st.toast("Log tersimpan ke Google Sheets ✅")
    except Exception as e:
        st.error(f"GAGAL menyimpan log: {e}")


if "chat" not in st.session_state:
    st.session_state.client = client
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-3.6-flash",
        config={"system_instruction": SYSTEM_PROMPT}
    )
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

pesan_siswa = st.chat_input("Ketik pertanyaanmu di sini...")

if pesan_siswa:
    st.session_state.messages.append({"role": "user", "content": pesan_siswa})
    with st.chat_message("user"):
        st.write(pesan_siswa)
    simpan_log("Eksperimen", "Siswa", pesan_siswa)

    jawaban = None
    percobaan_maksimal = 3
    for percobaan in range(percobaan_maksimal):
        try:
            response = st.session_state.chat.send_message(pesan_siswa)
            jawaban = response.text
            break
        except errors.ServerError:
            if percobaan < percobaan_maksimal - 1:
                with st.spinner(f"Server sedang sibuk, mencoba lagi... ({percobaan + 1}/{percobaan_maksimal})"):
                    time.sleep(5)
            else:
                jawaban = "Maaf, server sedang sangat sibuk. Silakan coba kirim pesanmu lagi beberapa saat lagi."

    st.session_state.messages.append({"role": "assistant", "content": jawaban})
    with st.chat_message("assistant"):
        st.write(jawaban)
    simpan_log("Eksperimen", "Chatbot", jawaban)
