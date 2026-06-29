import streamlit as st
import pandas as pd
import json, os, random, string, time, requests
import streamlit.components.v1 as components
from datetime import datetime

# ══════════════════════════════════════════
# KONFIGURASI
# ══════════════════════════════════════════
# Ganti dengan API Key Groq Anda sendiri untuk penilaian AI yang akurat.
GROQ_API_KEY   = "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"
DOSEN_PASSWORD = "dosen123"
FILE_TOPIK     = "data_topik.json"
FILE_NILAI     = "data_nilai.json"

st.set_page_config(page_title="EssaiKu", page_icon="✏️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap');
*,html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="collapsedControl"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
.stApp{background:#0f0c29!important;min-height:100vh}

.stTextInput input,.stTextArea textarea,.stNumberInput input{
  background:#fff!important;border:2px solid #e2e8f0!important;
  border-radius:12px!important;color:#1e293b!important;font-size:15px!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:#8b5cf6!important;box-shadow:0 0 0 3px rgba(139,92,246,.15)!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#94a3b8!important}

/* Label input — putih di background gelap */
.stTextInput label,.stTextArea label,.stNumberInput label,
.stSlider label,.stSelectbox label{
  color:#e2e8f0!important;font-size:13px!important;font-weight:600!important}

div.stButton>button{
  background:linear-gradient(135deg,#6366f1,#8b5cf6)!important;
  color:#fff!important;border:none!important;border-radius:12px!important;
  padding:12px 24px!important;font-weight:700!important;font-size:14px!important;
  box-shadow:0 4px 16px rgba(99,102,241,.4)!important;transition:all .2s!important}
div.stButton>button:hover{transform:translateY(-2px)!important}
div.stButton>button:disabled{opacity:.4!important;transform:none!important}

div[data-testid="metric-container"]{
  background:rgba(255,255,255,.08)!important;
  border:1px solid rgba(255,255,255,.15)!important;
  border-radius:16px!important;padding:20px!important}
div[data-testid="metric-container"] [data-testid="stMetricLabel"]{
  color:rgba(255,255,255,.65)!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{
  color:#fff!important;font-size:32px!important;font-weight:800!important}

.stProgress>div>div{
  background:linear-gradient(90deg,#6366f1,#a855f7)!important;border-radius:99px!important}
.stSelectbox>div>div{
  background:#fff!important;border-radius:12px!important;
  border:2px solid #e2e8f0!important;color:#1e293b!important}
.stAlert{border-radius:12px!important}
.stDataFrame{border-radius:12px!important;overflow:hidden!important}
.streamlit-expanderHeader{
  background:rgba(255,255,255,.08)!important;
  border:1px solid rgba(255,255,255,.12)!important;
  border-radius:12px!important;color:#fff!important;font-weight:600!important}

/* Teks umum di area konten dosen — putih */
.stMarkdown p,.stMarkdown li,.stMarkdown span{color:#e2e8f0}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════
def load_topik():
    try:
        if os.path.exists(FILE_TOPIK):
            with open(FILE_TOPIK,'r',encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return []

def save_topik(data):
    with open(FILE_TOPIK,'w',encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_nilai():
    try:
        if os.path.exists(FILE_NILAI):
            with open(FILE_NILAI,'r',encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return []

def save_nilai(data):
    with open(FILE_NILAI,'w',encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════
DEFAULTS = {
    'role'         : None,
    'nama'         : '',
    'menu'         : 'Dashboard',
    'topik_aktif'  : None,
    'soal_index'   : 0,
    'waktu_mulai'  : None,
    'semua_hasil'  : [],
    'hasil_terakhir': None,
    'draft_soal'   : [],
    'notif_kode'   : None,
    'f_matkul'     : '',
    'f_nama_topik' : '',
    'f_durasi'     : 30,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════
# AI PENILAIAN
# ══════════════════════════════════════════
def nilai_ai(jawaban, kunci):
    prompt = f"""Kamu sistem penilaian esai. Nilai HANYA dari kebenaran jawaban vs kunci.

KUNCI:
{kunci}

JAWABAN MAHASISWA:
{jawaban}

Balas HANYA JSON murni:
{{"skor":<0-100>,"ringkasan":"<1 kalimat>","feedback":["<p1>","<p2>","<p3>"],"yang_benar":"<benar>","yang_kurang":"<kurang atau tulis Jawaban sudah lengkap!>"}}

Skor: identik=95-100, semua poin=85-94, sebagian besar=70-84, sebagian kecil=50-69, sedikit=30-49, tidak relevan=0-29."""

    for model in ["llama-3.3-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it","llama3-8b-8192"]:
        for _ in range(2):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Content-Type":"application/json",
                             "Authorization":f"Bearer {GROQ_API_KEY}"},
                    json={"model":model,
                          "messages":[{"role":"user","content":prompt}],
                          "temperature":0.2,"max_tokens":800},
                    timeout=40)
                d = r.json()
                if "error" in d:
                    msg = d["error"].get("message","")
                    if r.status_code in [429,503] or any(
                        w in msg.lower() for w in ["rate","limit","quota","capacity"]):
                        time.sleep(7); continue
                    break
                teks = d["choices"][0]["message"]["content"].strip()
                teks = teks.replace("```json","").replace("```","").strip()
                if "{" in teks:
                    teks = teks[teks.index("{"):teks.rindex("}")+1]
                return json.loads(teks)
            except json.JSONDecodeError:
                time.sleep(2); continue
            except:
                time.sleep(2); break

    # Fallback lokal jika API AI gagal
    sw = {"yang","dan","di","ke","dari","ini","itu","atau","adalah","dengan",
          "untuk","pada","dalam","tidak","dapat","juga","oleh","akan"}
    kk = set(kunci.lower().split()) - sw
    kj = set(jawaban.lower().split()) - sw
    s  = min(100, int(len(kk&kj)/len(kk)*100)) if kk else 30
    return {"skor":s,
            "ringkasan":"⚠️ Dinilai lokal karena AI tidak tersedia.",
            "feedback":["Koneksi AI Groq gagal.",
                        "Skor dari kecocokan kata kunci.",
                        "Cek koneksi internet dan API key."],
            "yang_benar":"Lihat skor di atas.",
            "yang_kurang":"AI tidak tersedia untuk analisis detail."}

# ══════════════════════════════════════════
# HELPER: Kartu header ungu
# ══════════════════════════════════════════
def header_ungu(judul="EssaiKu", subjudul="", icon="✏️"):
    subtitle_html = (
        f"<div style=\"color:rgba(255,255,255,.75);font-size:13px;margin-top:6px;position:relative;\">{subjudul}</div>"
        if subjudul else ""
    )
    return f"""
    <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6,#a855f7);
      border-radius:24px 24px 0 0;padding:36px 32px 28px;text-align:center;
      position:relative;overflow:hidden;">
      <div style="position:absolute;top:-40px;right:-40px;width:130px;height:130px;
        border-radius:50%;background:rgba(255,255,255,.06);"></div>
      <div style="font-size:44px;margin-bottom:10px;position:relative;">{icon}</div>
      <div style="font-size:30px;font-weight:900;color:#fff;position:relative;">{judul}</div>
      {subtitle_html}
    </div>"""

# ══════════════════════════════════════════
# PAGE: LOGIN
# ══════════════════════════════════════════
def page_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(header_ungu("EssaiKu", "", icon="✏️"), unsafe_allow_html=True)

        st.markdown("""
        <div style="border-radius:0 0 24px 24px;padding:28px 32px 20px;margin-top:-2px;
          background:linear-gradient(135deg,#110e24,#20164a);box-shadow:0 32px 80px rgba(0,0,0,.35);">
          <div style="color:#ffffff;font-size:18px;font-weight:800;margin-bottom:6px;">
            👨‍🏫 Masuk sebagai Dosen
          </div>
          <div style="color:rgba(255,255,255,.72);font-size:13px;margin-bottom:18px;">
            Kelola soal dan pantau nilai mahasiswa
          </div>
          <div style="color:rgba(255,255,255,.8);font-size:13px;">
            Password dosen: <span style="font-weight:800;">dosen123</span>
          </div>
        </div>""", unsafe_allow_html=True)

        nama = st.text_input("Nama Dosen", placeholder="Masukkan nama kamu...", key="inp_nama")
        pwd  = st.text_input("Password", type="password", placeholder="dosen123", key="inp_pwd")

        if st.button("🔑 Masuk ke Dashboard", use_container_width=True):
            if not nama.strip():
                st.warning("⚠️ Masukkan nama dosen!")
            elif pwd == DOSEN_PASSWORD:
                st.session_state.role = "Dosen"
                st.session_state.nama = nama.strip()
                st.session_state.menu = "Dashboard"
                st.rerun()
            else:
                st.error("❌ Password salah!")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""<div style="text-align:center;margin-top:14px;
          color:#94a3b8;font-size:12px;">
          Mahasiswa? Buka link yang dibagikan dosenmu
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# PAGE: MAHASISWA — buka via ?kode=XXXXX
# ══════════════════════════════════════════
def page_mahasiswa_link(kode):
    semua = load_topik()
    kode  = str(kode).strip() if kode else ""
    topik = next((t for t in semua if str(t.get('kode','')).strip() == kode), None)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(f"""
        <div style="margin-top:32px;border-radius:24px;overflow:hidden;
          box-shadow:0 32px 80px rgba(0,0,0,.55);">
          {header_ungu()}
        </div>""", unsafe_allow_html=True)

        if topik is None:
            st.error(f"❌ Link tidak valid. Kode yang diterima: '{kode}'")
            return

        total = len(topik['soal_list'])

        st.markdown(f"""
        <div style="background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);
          border-radius:16px;padding:18px 20px 22px;margin-bottom:18px;">
          <div style="color:#e0d7ff;font-size:11px;font-weight:700;margin-bottom:4px;">
            📚 {topik['mata_kuliah']}</div>
          <div style="color:#fff;font-size:20px;font-weight:800;margin-bottom:10px;">
            {topik['nama_topik']}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <span style="background:rgba(255,255,255,.1);color:#d8b4fe;border-radius:8px;
              padding:6px 10px;font-size:12px;font-weight:700;">
              📝 {total} Soal</span>
            <span style="background:rgba(255,255,255,.1);color:#fde68a;border-radius:8px;
              padding:6px 10px;font-size:12px;font-weight:700;">
              ⏱ {topik.get('durasi',30)} mnt/soal</span>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="color:#e2e8f0;font-size:13px;font-weight:700;margin:16px 0 4px;
          line-height:1.4;">
          👤 Masukkan nama kamu
        </div>""", unsafe_allow_html=True)

        nama = st.text_input("", placeholder="Nama lengkap...",
                             label_visibility="collapsed", key="nama_mhs")

        if st.button("🚀 Kerjakan", use_container_width=True):
            if nama.strip():
                st.session_state.topik_aktif = topik
                st.session_state.soal_index  = 0
                st.session_state.semua_hasil = []
                st.session_state.waktu_mulai = time.time()
                st.session_state.nama        = nama.strip()
                st.session_state.role        = "Mahasiswa"
                st.rerun()
            else:
                st.warning("⚠️ Masukkan nama dulu!")

# ══════════════════════════════════════════
# PAGE: KERJAKAN SOAL (DISEMPURNAKAN - TATA LETAK FOKUS KIRI + TIMER AMAN)
# ══════════════════════════════════════════
def page_kerjakan():
    topik = st.session_state.topik_aktif
    idx   = st.session_state.soal_index
    soal  = topik['soal_list'][idx]
    total = len(topik['soal_list'])
    
    # Hitung durasi awal
    durasi_detik = int(topik.get('durasi', 30) * 60)
    sisa = max(0, durasi_detik - int(time.time() - st.session_state.waktu_mulai))

    # Cek parameter otomatis dari Javascript jika waktu habis
    if st.query_params.get("timeout") == "true":
        st.query_params.clear()
        st.error("⏰ Waktu habis! Jawaban dikumpulkan otomatis.")
        sisa = 0

    # TATA LETAK BARIS ATAS: INFO MAHASISWA & SOAL (KIRI), TIMER & BATALKAN (KANAN)
    col_kiri, col_kanan = st.columns([2, 1])

    with col_kiri:
        # Pindahkan info soal dan mahasiswa ke kiri atas agar sejajar timer di kanan
        st.markdown(f"""
        <div style="padding:10px 0 6px;">
          <div style="color:rgba(255,255,255,.4);font-size:12px;
            text-transform:uppercase;letter-spacing:.1em; font-weight: 700;">
            {topik['mata_kuliah'].upper()} · {topik['nama_topik'].upper()}
          </div>
          <div style="color:#fff; font-size:26px; font-weight:800; margin-top:2px;">
            EssaiKu — Soal {idx+1} dari {total}
          </div>
          <div style="color:rgba(255,255,255,.6); font-size:14px; margin-top:4px;">
            👤 Mahasiswa: {st.session_state.nama}
          </div>
        </div>""", unsafe_allow_html=True)

    with col_kanan:
        c_timer, c_batal = st.columns([1.6, 1])
        with c_timer:
            # Menggunakan JS Timer Komponen agar ketikan di browser tidak patah/macet akibat rerun
            timer_html = f"""
            <div id="countdown-box" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius:18px;
              padding:12px; text-align:center; box-shadow:0 4px 16px rgba(0,0,0,.3); font-family: 'Plus Jakarta Sans', sans-serif;">
              <div style="color:rgba(255,255,255,.7); font-size:9px; font-weight:700; letter-spacing:.1em;">SISA WAKTU SOAL INI</div>
              <div id="timer-display" style="color:#fff; font-size:32px; font-weight:900; font-family:monospace; line-height:1.2;">--:--</div>
            </div>
            <script>
                var seconds = {sisa};
                function updateTimer() {{
                    var m = Math.floor(seconds / 60);
                    var s = seconds % 60;
                    m = m < 10 ? "0" + m : m;
                    s = s < 10 ? "0" + s : s;
                    document.getElementById("timer-display").innerText = m + ":" + s;
                    
                    if (seconds <= 60) {{
                        document.getElementById("countdown-box").style.background = "linear-gradient(135deg, #ef4444, #b91c1c)";
                    }} else if (seconds <= 300) {{
                        document.getElementById("countdown-box").style.background = "linear-gradient(135deg, #f59e0b, #d97706)";
                    }}

                    if (seconds <= 0) {{
                        // Kirim query params untuk trigger autosubmit di Streamlit tanpa freeze
                        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: true}}, '*');
                        var url = new URL(window.parent.location.href);
                        url.searchParams.set('timeout', 'true');
                        window.parent.location.href = url.href;
                    }} else {{
                        seconds--;
                        setTimeout(updateTimer, 1000);
                    }}
                }}
                updateTimer();
            </script>
            """
            components.html(timer_html, height=100)
            
        with c_batal:
            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
            if st.button("🚫 Batalkan", use_container_width=True):
                st.session_state.role        = None
                st.session_state.topik_aktif = None
                st.session_state.waktu_mulai = None
                st.session_state.semua_hasil = []
                st.session_state.soal_index  = 0
                st.rerun()

    # GARIS PEMBATAS ELEGAN
    st.markdown("<hr style='border-color:rgba(255,255,255,.1); margin:10px 0 25px 0;'>", unsafe_allow_html=True)

    # KOTAK PERTANYAAN (PENUH MELINTAS JIKA PERLU)
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:20px;
      padding:28px 32px;box-shadow:0 8px 24px rgba(99,102,241,.3);margin-bottom:25px;">
      <div style="color:rgba(255,255,255,.65);font-size:11px;text-transform:uppercase;
        letter-spacing:.12em;margin-bottom:12px;font-weight:800;">📋 PERTANYAAN {idx+1}</div>
      <div style="color:#fff;font-size:20px;font-weight:700;line-height:1.6;">
        {soal['soal']}
      </div>
    </div>""", unsafe_allow_html=True)

    # INPUT JAWABAN MAHASISWA (Sekarang aman untuk mengetik berkat JS timer)
    jawaban  = st.text_area("✍️ Jawaban kamu:", height=280,
                           placeholder="Tulis jawaban esai selengkap mungkin...",
                           key=f"jwb_{idx}")
    
    min_kata = soal.get('min_kata', 20)
    jml      = len(jawaban.split()) if jawaban.strip() else 0
    pct      = min(100, int(jml / min_kata * 100))
    warna_p  = "#22c55e" if jml >= min_kata else "#a78bfa"
    
    # Indikator Progress Word Count
    st.progress(pct)
    st.markdown(f"<div style='text-align:right;color:{warna_p};font-size:13px;"
                f"font-weight:600;margin-top:-6px;margin-bottom:20px;'>{jml} / {min_kata} kata minimum</div>",
                unsafe_allow_html=True)

    # TOMBOL NAVIGASI BAWAH
    lanjut    = idx < total - 1
    label_btn = "Lanjut ke Soal Berikutnya ➡️" if lanjut else "Kumpulkan Jawaban ➡️"
    
    # Paksa kumpul jika sisa waktu habis (0) atau tombol ditekan dan syarat terpenuhi
    kumpul = st.button(label_btn, use_container_width=True, disabled=(jml < min_kata and sisa > 0))

    if sisa <= 0:
        kumpul = True

    if kumpul and jawaban.strip():
        waktu_k = int((time.time() - st.session_state.waktu_mulai) / 60)

        kotak = st.empty()
        kotak.markdown("""
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);
          border-radius:14px;padding:24px;text-align:center;color:#fff;margin:12px 0;">
          <div style="font-size:28px;margin-bottom:8px;">🤖</div>
          <div style="font-size:15px;font-weight:700;">AI sedang menilai jawaban kamu...</div>
          <div style="font-size:12px;opacity:.75;margin-top:4px;">Tunggu sebentar ya...</div>
        </div>""", unsafe_allow_html=True)

        # Panggil fungsi AI untuk menilai
        hasil_ai = nilai_ai(jawaban, soal['kunci'])
        kotak.empty()

        st.session_state.semua_hasil.append({
            'soal': soal, 'hasil_ai': hasil_ai, 'waktu': waktu_k
        })

        if lanjut:
            st.session_state.soal_index  = idx + 1
            st.session_state.waktu_mulai = time.time()
            st.rerun()
        else:
            semua = st.session_state.semua_hasil
            avg   = sum(h['hasil_ai']['skor'] for h in semua) / len(semua)

            nv = load_nilai()
            nv.append({
                'Nama'             : st.session_state.nama,
                'Kode Topik'       : topik['kode'],
                'Mata Kuliah'      : topik['mata_kuliah'],
                'Nama Topik'       : topik['nama_topik'],
                'Jumlah Soal'      : total,
                'Skor Rata-rata'   : round(avg, 1),
                'Waktu Total (mnt)': sum(h['waktu'] for h in semua),
                'Tanggal'          : datetime.now().strftime("%d/%m/%Y %H:%M"),
            })
            save_nilai(nv)

            st.session_state.hasil_terakhir = {
                'semua': semua, 'topik': topik, 'avg': avg
            }
            st.session_state.role        = "Hasil"
            st.session_state.topik_aktif = None
            st.session_state.waktu_mulai = None
            st.rerun()

# ══════════════════════════════════════════
# PAGE: HASIL
# ══════════════════════════════════════════
def page_hasil():
    r = st.session_state.hasil_terakhir
    if not r:
        st.session_state.role = None
        st.rerun()

    semua = r['semua']
    topik = r['topik']
    avg   = r['avg']

    def grade(s):
        if s >= 80: return "#059669,#34d399", "🏆", "Luar Biasa!"
        if s >= 65: return "#2563eb,#60a5fa", "👍", "Bagus!"
        if s >= 50: return "#d97706,#fbbf24", "📖", "Cukup Baik"
        return "#dc2626,#f87171", "💪", "Tetap Semangat!"

    g, e, p = grade(avg)
    _, col, _ = st.columns([1, 3, 1])
    with col:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{g});border-radius:24px;
          padding:44px;text-align:center;margin:16px 0 20px;
          box-shadow:0 12px 40px rgba(0,0,0,.25);">
          <div style="color:rgba(255,255,255,.85);font-size:16px;
            font-weight:700;margin-bottom:8px;">{e} {p}</div>
          <div style="color:#fff;font-size:80px;font-weight:900;line-height:1;">
            {avg:.0f}<span style="font-size:34px;opacity:.65">/100</span>
          </div>
          <div style="color:rgba(255,255,255,.7);font-size:13px;margin-top:10px;">
            Rata-rata {len(semua)} soal · 📚 {topik['mata_kuliah']} · 👤 {st.session_state.nama}
          </div>
        </div>""", unsafe_allow_html=True)

        for i, h in enumerate(semua):
            ai  = h['hasil_ai']
            tot = ai['skor']
            bg  = "#f0fdf4" if tot >= 80 else ("#fffbeb" if tot >= 50 else "#fef2f2")
            bc  = "#86efac" if tot >= 80 else ("#fcd34d" if tot >= 50 else "#fca5a5")
            tc  = "#166534" if tot >= 80 else ("#92400e" if tot >= 50 else "#991b1b")

            st.markdown(f"""
            <div style="background:{bg};border:1.5px solid {bc};
              border-radius:14px;padding:16px 20px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;
                align-items:center;gap:8px;">
                <div style="flex:1;">
                  <div style="color:{tc};font-weight:700;font-size:13px;margin-bottom:3px;">
                    Soal {i+1}: {h['soal']['soal'][:60]}...
                  </div>
                  <div style="color:{tc};font-size:12px;opacity:.85;">{ai['ringkasan']}</div>
                </div>
                <div style="color:{tc};font-size:28px;font-weight:900;white-space:nowrap;">
                  {tot}<span style="font-size:13px;opacity:.7">/100</span>
                </div>
              </div>
              <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">
                <div style="flex:1;background:rgba(255,255,255,.6);
                  border-radius:8px;padding:10px 12px;">
                  <div style="color:{tc};font-size:11px;font-weight:700;margin-bottom:4px;">
                    ✅ Yang Sudah Benar
                  </div>
                  <div style="color:{tc};font-size:12px;line-height:1.5;">
                    {ai['yang_benar']}
                  </div>
                </div>
                <div style="flex:1;background:rgba(255,255,255,.6);
                  border-radius:8px;padding:10px 12px;">
                  <div style="color:{tc};font-size:11px;font-weight:700;margin-bottom:4px;">
                    📌 Yang Perlu Ditambah
                  </div>
                  <div style="color:{tc};font-size:12px;line-height:1.5;">
                    {ai['yang_kurang'] if ai['yang_kurang'] not in ['-','',None]
                     else 'Jawaban sudah lengkap!'}
                  </div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

            for j, fb in enumerate(ai['feedback']):
                st.markdown(f"""
                <div style="background:rgba(0,0,0,.04);border-radius:6px;
                  padding:6px 10px;margin-bottom:4px;color:{tc};font-size:12px;">
                  <span style="background:{tc};color:#fff;border-radius:4px;
                    padding:1px 6px;font-size:10px;font-weight:700;margin-right:6px;">
                    {j+1}</span>{fb}
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 Selesai", use_container_width=True):
            st.session_state.hasil_terakhir = None
            st.session_state.semua_hasil    = []
            st.session_state.soal_index     = 0
            st.session_state.role           = None
            st.rerun()

# ══════════════════════════════════════════
# PAGE: DOSEN
# ══════════════════════════════════════════
def page_dosen():
    import plotly.express as px

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1040,#2d1b69);
      border-radius:16px;padding:14px 20px;margin-bottom:20px;
      border:1px solid rgba(139,92,246,.3);
      display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:38px;height:38px;border-radius:10px;
          background:linear-gradient(135deg,#6366f1,#8b5cf6);
          display:flex;align-items:center;justify-content:center;font-size:20px;">✏️</div>
        <div>
          <div style="color:#fff;font-size:15px;font-weight:800;">EssaiKu</div>
          <div style="color:rgba(255,255,255,.45);font-size:11px;">
            👨‍🏫 {st.session_state.nama} · Panel Dosen</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    menus = ["📊 Dashboard", "📝 Buat Soal", "🗂 Daftar Soal", "📈 Rekap Nilai"]
    cols  = st.columns(len(menus) + 1)

    for i, (col, label) in enumerate(zip(cols[:-1], menus)):
        with col:
            nama_menu = label.split(" ", 1)[1]
            aktif     = (st.session_state.menu == nama_menu)
            if aktif:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);
                  border-radius:10px;padding:9px 4px;text-align:center;
                  color:#fff;font-size:13px;font-weight:700;
                  border:1.5px solid #8b5cf6;pointer-events:none;">{label}</div>""",
                  unsafe_allow_html=True)
            else:
                if st.button(label, key=f"mn_{i}", use_container_width=True):
                    st.session_state.menu = nama_menu
                    st.rerun()

    with cols[-1]:
        if st.button("🚪 Keluar", use_container_width=True, key="btn_keluar"):
            st.session_state.role = None
            st.session_state.menu = "Dashboard"
            st.rerun()

    h = st.session_state.menu

    st.markdown(f"""
    <div style="margin:16px 0 14px;">
      <div style="color:#fff;font-size:22px;font-weight:900;">{h}</div>
      <div style="width:36px;height:3px;background:linear-gradient(90deg,#6366f1,#8b5cf6);
        border-radius:99px;margin-top:5px;"></div>
    </div>""", unsafe_allow_html=True)

    semua_topik = load_topik()
    semua_nilai = load_nilai()
    topik_saya  = [t for t in semua_topik if t.get('dosen') == st.session_state.nama]

    if h == "Dashboard":
        # PERBAIKAN 2: Deteksi alamat website otomatis agar link mahasiswa akurat
        try:
            # Mencoba mengambil domain website aktif dari header request
            domain_aktif = st.context.headers.get("host", "localhost:8501")
        except:
            # Fallback jika gagal (misal berjalan di versi streamlit lama)
            domain_aktif = "localhost:8501"

        nilai_saya = [n for n in semua_nilai
                      if n.get('Kode Topik') in [t['kode'] for t in topik_saya]]
        avg = (sum(n['Skor Rata-rata'] for n in nilai_saya) / len(nilai_saya)
               if nilai_saya else 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("📝 Topik Dibuat",   len(topik_saya))
        c2.metric("📋 Jawaban Masuk",  len(nilai_saya))
        c3.metric("⭐ Rata-rata Nilai", f"{avg:.1f}")

        st.markdown("<br>", unsafe_allow_html=True)

        if topik_saya:
            for t in topik_saya:
                nv_t = [n for n in semua_nilai if n.get('Kode Topik') == t['kode']]
                av_t = (sum(n['Skor Rata-rata'] for n in nv_t) / len(nv_t) if nv_t else 0)

                st.markdown(f"""
                <div style="background:rgba(255,255,255,.07);
                  border:1px solid rgba(255,255,255,.12);
                  border-radius:16px;padding:20px;margin-bottom:14px;">
                  <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;gap:12px;flex-wrap:wrap;">
                    <div style="flex:1;min-width:180px;">
                      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
                        <span style="background:rgba(139,92,246,.3);color:#c4b5fd;
                          border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;">
                          📚 {t['mata_kuliah']}</span>
                        <span style="background:rgba(255,255,255,.1);color:#e2e8f0;
                          border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;">
                          📝 {len(t['soal_list'])} soal</span>
                        <span style="background:rgba(255,255,255,.1);color:#e2e8f0;
                          border-radius:6px;padding:2px 8px;font-size:11px;font-weight:700;">
                          👥 {len(nv_t)} jawaban</span>
                      </div>
                      <div style="color:#fff;font-size:16px;font-weight:800;margin-bottom:10px;">
                        {t['nama_topik']}
                      </div>
                      <div style="background:rgba(255,255,255,.05);
                        border:1px dashed rgba(255,255,255,.2);
                        border-radius:8px;padding:10px 14px;">
                        <div style="color:rgba(255,255,255,.4);font-size:10px;
                          font-weight:700;margin-bottom:4px;">🔗 LINK UNTUK MAHASISWA</div>
                        <div style="color:#a78bfa;font-size:14px;font-weight:700;
                          word-break:break-all;" id="link_{t['kode']}">
                          {domain_aktif}/?kode={t['kode']}
                        </div>
                        <div style="color:rgba(255,255,255,.3);font-size:11px;margin-top:4px;">
                          Salin link ini dan bagikan ke mahasiswa. Berubah otomatis jika online.
                        </div>
                      </div>
                    </div>
                    <div style="background:rgba(99,102,241,.25);
                      border:1px solid rgba(139,92,246,.4);
                      border-radius:10px;padding:12px 16px;text-align:center;min-width:80px;">
                      <div style="color:#c4b5fd;font-size:10px;font-weight:700;margin-bottom:3px;">
                        KODE</div>
                      <div style="color:#fff;font-size:22px;font-weight:900;font-family:monospace;">
                        {t['kode']}</div>
                    </div>
                  </div>
                  {f'<div style="background:rgba(34,197,94,.1);border-radius:8px;padding:6px 12px;margin-top:10px;color:#86efac;font-size:12px;font-weight:700;">⭐ Rata-rata nilai: {av_t:.1f}/100</div>' if nv_t else ''}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(255,255,255,.04);
              border:1px dashed rgba(255,255,255,.15);
              border-radius:16px;padding:48px;text-align:center;margin-top:20px;">
              <div style="font-size:44px;margin-bottom:12px;">📝</div>
              <div style="color:#fff;font-size:16px;font-weight:700;margin-bottom:6px;">
                Belum Ada Soal</div>
              <div style="color:rgba(255,255,255,.4);font-size:13px;">
                Klik "📝 Buat Soal" di menu atas</div>
            </div>""", unsafe_allow_html=True)

    elif h == "Buat Soal":
        if st.session_state.notif_kode:
            # PERBAIKAN 2 (Juga diterapkan pada notifikasi sukses buat soal)
            try:
                domain_aktif = st.context.headers.get("host", "localhost:8501")
            except:
                domain_aktif = "localhost:8501"

            kode_n = st.session_state.notif_kode
            topik_n = next((t for t in load_topik() if t['kode'] == kode_n), None)
            if topik_n:
                st.success(f"✅ Topik '{topik_n['nama_topik']}' berhasil disimpan ({len(topik_n['soal_list'])} soal, 1 link)!")
                st.markdown(f"""
                <div style="background:rgba(34,197,94,.1);border:1.5px solid rgba(34,197,94,.3);
                  border-radius:14px;padding:20px;text-align:center;margin-bottom:20px;">
                  <div style="color:#86efac;font-size:13px;font-weight:700;margin-bottom:6px;">
                    🔗 Link untuk semua mahasiswa ({len(topik_n['soal_list'])} soal, 1 link)
                  </div>
                  <div style="color:#a78bfa;font-size:16px;font-weight:800;margin-bottom:10px;">
                    {domain_aktif}/?kode={kode_n}
                  </div>
                  <div style="color:#86efac;font-size:28px;font-weight:900;
                    font-family:monospace;letter-spacing:8px;">{kode_n}</div>
                </div>""", unsafe_allow_html=True)
            if st.button("➕ Buat Topik Soal Baru", use_container_width=True):
                st.session_state.notif_kode   = None
                st.session_state.draft_soal   = []
                st.session_state.f_matkul     = ''
                st.session_state.f_nama_topik = ''
                st.session_state.f_durasi     = 30
                st.rerun()

        else:
            st.markdown("""
            <div style="color:#c4b5fd;font-size:11px;font-weight:700;
              text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px;">
              LANGKAH 1 — Info Topik / Mata Kuliah
            </div>""", unsafe_allow_html=True)

            with st.form("form_info"):
                c1, c2 = st.columns(2)
                f_mk  = c1.text_input("Mata Kuliah *", value=st.session_state.f_matkul, placeholder="Contoh: Sistem Cerdas")
                f_nm  = c2.text_input("Nama Topik / Ujian *", value=st.session_state.f_nama_topik, placeholder="Contoh: UTS Deep Learning")
                f_dur = st.number_input("Durasi per Soal (menit)", min_value=1, max_value=300, value=st.session_state.f_durasi)
                ok    = st.form_submit_button("✅ Simpan Info", use_container_width=True)

            if ok:
                if f_mk.strip() and f_nm.strip():
                    st.session_state.f_matkul     = f_mk.strip()
                    st.session_state.f_nama_topik = f_nm.strip()
                    st.session_state.f_durasi      = int(f_dur)
                    st.rerun()
                else:
                    st.warning("⚠️ Isi Mata Kuliah dan Nama Topik!")

            if st.session_state.f_matkul and st.session_state.f_nama_topik:
                st.markdown(f"""
                <div style="background:rgba(139,92,246,.15);border:1px solid rgba(139,92,246,.3);
                  border-radius:10px;padding:10px 14px;margin-bottom:16px;">
                  <span style="color:#c4b5fd;font-weight:700;">
                    📦 {st.session_state.f_nama_topik}</span>
                  <span style="color:rgba(255,255,255,.5);font-size:12px;">
                    · {st.session_state.f_matkul}
                    · {st.session_state.f_durasi} mnt/soal</span>
                </div>""", unsafe_allow_html=True)

                if st.session_state.draft_soal:
                    n_draft = len(st.session_state.draft_soal)
                    st.markdown(f"""
                    <div style="color:#86efac;font-size:13px;font-weight:700;margin-bottom:8px;">
                      ✅ {n_draft} soal sudah ditambahkan:
                    </div>""", unsafe_allow_html=True)
                    for i, ds in enumerate(st.session_state.draft_soal):
                        dc1, dc2 = st.columns([6, 1])
                        with dc1:
                            st.markdown(f"""
                            <div style="background:rgba(255,255,255,.06);
                              border:1px solid rgba(255,255,255,.1);
                              border-radius:8px;padding:8px 12px;margin-bottom:5px;">
                              <span style="background:#6366f1;color:#fff;border-radius:4px;
                                padding:1px 6px;font-size:10px;font-weight:700;
                                margin-right:6px;">Soal {i+1}</span>
                              <span style="color:#e2e8f0;font-size:13px;">
                                {ds['soal'][:80]}...</span>
                            </div>""", unsafe_allow_html=True)
                        with dc2:
                            if st.button("🗑️", key=f"rm_{i}"):
                                st.session_state.draft_soal.pop(i)
                                st.rerun()

                no_soal = len(st.session_state.draft_soal) + 1
                st.markdown(f"""
                <div style="color:#c4b5fd;font-size:11px;font-weight:700;
                  text-transform:uppercase;letter-spacing:.1em;margin:14px 0 8px;">
                  LANGKAH 2 — Tambah Soal {no_soal} (bisa sebanyak apapun)
                </div>""", unsafe_allow_html=True)

                with st.form("form_soal", clear_on_submit=True):
                    soal_t  = st.text_area("Pertanyaan *", height=100, placeholder="Tulis pertanyaan esai di sini...")
                    kunci_t = st.text_area("Kunci Jawaban *", height=130, placeholder="Tulis kunci jawaban selengkap mungkin. Semakin detail → AI semakin akurat.")
                    min_w   = st.number_input("Minimum kata jawaban mahasiswa", min_value=5, max_value=500, value=20)
                    add_btn = st.form_submit_button("➕ Tambah Soal Ini", use_container_width=True)

                if add_btn:
                    if soal_t.strip() and kunci_t.strip():
                        st.session_state.draft_soal.append({
                            'soal'    : soal_t.strip(),
                            'kunci'   : kunci_t.strip(),
                            'min_kata': int(min_w),
                        })
                        st.rerun()
                    else:
                        st.warning("⚠️ Isi pertanyaan dan kunci jawaban!")

                if st.session_state.draft_soal:
                    jml = len(st.session_state.draft_soal)
                    st.markdown(f"""
                    <div style="color:#a78bfa;font-size:13px;margin:12px 0 6px;">
                      💡 Sudah {jml} soal. Bisa tambah lebih banyak atau langsung simpan.
                    </div>""", unsafe_allow_html=True)

                    if st.button(f"💾 Simpan Topik ({jml} Soal) & Generate 1 Link", use_container_width=True):
                        kode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        topik_baru = {
                            'kode'       : kode,
                            'dosen'      : st.session_state.nama,
                            'mata_kuliah': st.session_state.f_matkul,
                            'nama_topik' : st.session_state.f_nama_topik,
                            'durasi'     : st.session_state.f_durasi,
                            'soal_list'  : list(st.session_state.draft_soal),
                            'dibuat'     : datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }
                        semua_topik_baru = load_topik()
                        semua_topik_baru.append(topik_baru)
                        save_topik(semua_topik_baru)

                        st.session_state.notif_kode   = kode
                        st.session_state.draft_soal   = []
                        st.session_state.f_matkul     = ''
                        st.session_state.f_nama_topik = ''
                        st.rerun()
            else:
                st.info("ℹ️ Isi Mata Kuliah dan Nama Topik dulu di atas, lalu klik Simpan Info.")

    elif h == "Daftar Soal":
        if not topik_saya:
            st.info("Belum ada topik. Buat di menu '📝 Buat Soal'!")
        else:
            try:
                domain_aktif = st.context.headers.get("host", "localhost:8501")
            except:
                domain_aktif = "localhost:8501"

            st.markdown(f"""
            <div style="color:rgba(255,255,255,.5);font-size:13px;margin-bottom:12px;">
              Total {len(topik_saya)} topik aktif
            </div>""", unsafe_allow_html=True)

            for t in topik_saya:
                nv_t = [n for n in semua_nilai if n.get('Kode Topik') == t['kode']]
                with st.expander(f"📦 {t['nama_topik']} · {t['mata_kuliah']} · {len(t['soal_list'])} soal · {len(nv_t)} jawaban"):
                    st.markdown(f"**Kode:** `{t['kode']}`")
                    # Link Mahasiswa juga diperbaiki di sini
                    st.markdown(f"**Link:** `{domain_aktif}/?kode={t['kode']}`")
                    st.markdown(f"**Durasi:** {t.get('durasi',30)} mnt/soal  | **Dibuat:** {t.get('dibuat','-')}")
                    st.markdown("---")

                    for i, sq in enumerate(t['soal_list']):
                        st.markdown(f"**Soal {i+1}:** {sq['soal']}")
                        st.markdown(f"*Kunci:* {sq['kunci'][:100]}...")
                        st.markdown(f"*Min kata:* {sq['min_kata']}")
                        if i < len(t['soal_list']) - 1:
                            st.markdown("---")

                    if st.button("🗑️ Hapus Topik Ini", key=f"del_{t['kode']}"):
                        semua_baru = [x for x in semua_topik if x['kode'] != t['kode']]
                        save_topik(semua_baru)
                        st.rerun()

    elif h == "Rekap Nilai":
        nilai_saya = [n for n in semua_nilai if n.get('Kode Topik') in [t['kode'] for t in topik_saya]]

        if not nilai_saya:
            st.info("Belum ada jawaban masuk dari mahasiswamu.")
        else:
            df = pd.DataFrame(nilai_saya)
            opsi = ["Semua Topik"] + [f"{t['nama_topik']} ({t['kode']})" for t in topik_saya]
            pilih = st.selectbox("🔍 Filter topik:", opsi)
            if pilih != "Semua Topik":
                kode_f = pilih.split("(")[-1].replace(")", "").strip()
                df     = df[df['Kode Topik'] == kode_f]

            if len(df) > 0:
                sa, sb, sc = st.columns(3)
                sa.metric("👥 Mahasiswa", len(df))
                sb.metric("⭐ Rata-rata", f"{df['Skor Rata-rata'].mean():.1f}")
                sc.metric("🏆 Tertinggi", f"{df['Skor Rata-rata'].max():.1f}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, height=300)

            ga, gb = st.columns(2)
            with ga:
                fig = px.histogram(df, x='Skor Rata-rata', nbins=10, title='Distribusi Nilai', color_discrete_sequence=['#8b5cf6'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,.05)', font=dict(color='#e2e8f0'), title_font_color='#fff',
                    xaxis=dict(color='#e2e8f0', gridcolor='rgba(255,255,255,.1)'), yaxis=dict(color='#e2e8f0', gridcolor='rgba(255,255,255,.1)'))
                st.plotly_chart(fig, use_container_width=True)
            with gb:
                fig2 = px.box(df, y='Skor Rata-rata', title='Sebaran Nilai', color_discrete_sequence=['#6366f1'])
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,.05)', font=dict(color='#e2e8f0'), title_font_color='#fff',
                    yaxis=dict(color='#e2e8f0', gridcolor='rgba(255,255,255,.1)'))
                st.plotly_chart(fig2, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Rekap Nilai (CSV)", data=csv, file_name=f"rekap_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)

# ══════════════════════════════════════════════════════════════
# ROUTING UTAMA
# ══════════════════════════════════════════════════════════════
try:
    _params  = st.query_params
    url_kode = _params.get("kode", None)
    if url_kode is not None and str(url_kode).strip() == "":
        url_kode = None
    if url_kode is not None:
        url_kode = str(url_kode).strip()
except:
    url_kode = None

role = st.session_state.role

if url_kode:
    if role == "Mahasiswa" and st.session_state.topik_aktif:
        page_kerjakan()
    elif role == "Hasil":
        page_hasil()
    else:
        page_mahasiswa_link(url_kode)
elif role == "Mahasiswa" and st.session_state.topik_aktif:
    page_kerjakan()
elif role == "Hasil":
    page_hasil()
elif role == "Dosen":
    page_dosen()
else:
    page_login()