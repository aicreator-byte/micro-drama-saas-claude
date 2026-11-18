Perbaiki 1 temuan tersisa dari verifikasi independen sesudah PHASE2-FIX-REPORT.md (migrasi SUDAH BENAR: server start di DB segar + DB lama, pytest 54/54, build 19/19, smoke live 24/25).

TEMUAN (wajib): story generate LLM GAGAL — status=failed, error di DB: `All providers failed: [{'provider': 'nvidia-nim-1', 'error': "Invalid port: ':1]'"}]`.
- Penyebab (terverifikasi): `httpx.AsyncClient(timeout=120.0)` di `app/services/ai_client.py` baris 105 memakai `trust_env=True` (default) — ia membaca proxy dari env, dan entri `no_proxy` di lingkungan ini berisi IPv6 berkurung (`[::1]`, `[fd8b:...]`) yang membuat parser proxy httpx gagal dengan `InvalidURL("Invalid port: ':1]'")`.
- BUKTI kunci + endpoint sehat: panggilan langsung dengan proxy eksplisit `httpx.AsyncClient(proxy='http://hatch-egress-proxy:3128')` ke `https://integrate.api.nvidia.com/v1/chat/completions` mengembalikan HTTP 200. Jadi bukan kunci/endpoint yang rusak. Klaim "tokens_used 1847" di laporan fix sebelumnya tidak bisa direproduksi di lingkungan ini — kemungkinan builder mengetes dengan env berbeda.
- Perbaiki: bangun httpx client dengan proxy eksplisit dari env (`HTTPS_PROXY`/`https_proxy`) dan JANGAN andalkan parsing env httpx (mis. `trust_env=False` + `proxy=os.getenv(...)`, atau tangkap dan abaikan entri no_proxy yang rusak). Perbaikan harus di kode ai_client (bukan di env), supaya jalan di lingkungan ini.

TUGAS (hanya ini, kerja HANYA di /home/hatch/workspace/micro-drama-saas/claude/):
1. Perbaiki konstruksi httpx client di ai_client (semua tempat yang memanggil API eksternal). JANGAN ubah: migrasi, auth/JWT, enkripsi, route/skema respons, tes yang sudah ada. JANGAN sentuh security. JANGAN sentuh kaki lain.
2. PERINGATAN — JANGAN pakai `pkill -f` untuk mematikan server tes: pola pkill bisa cocok dengan shell agen sendiri dan membunuh agen. Matikan server tes dengan PID eksplisit (tangkap `$!` saat start, lalu `kill <PID>`), atau cek port dengan curl saja tanpa mematikan.
3. SEBELUM menyatakan selesai, jalankan sendiri tes live di DB SEGAR: nyalakan server (uvicorn + kunci Nvidia asli dari env), lalu story generate (generation_type story_idea, context berisi kata kunci unik) → status completed DAN `model_used` ultra-550b DAN `tokens_used` > 0 DAN `generated_output` berisi kata kunci itu (BUKTI LLM nyata). Simpan bukti di laporan.
PENERIMAAN: pytest 54/54 (tidak boleh turun); story generate LLM nyata completed dengan bukti di atas; frontend `npm run build` exit 0.
Tulis PHASE2-FIX2-REPORT.md (apa yang diubah + bukti story generate).
