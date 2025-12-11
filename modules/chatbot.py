# Chatbot wrapper: uses Gemini if available, else simple rule-based fallback
def reply(question):
    # Mock answers for common queries
    q=question.lower()
    if 'minyak' in q or 'jelantah' in q:
        return '- Harga minyak jelantah: Rp 6.500 - 7.200 per liter (estimasi)\\n- Simpan di botol tertutup sebelum penjemputan.'
    if 'cara' in q and 'pilah' in q:
        return '- Pisahkan plastik, kertas, logam, kaca. Cuci/bersihkan plastik yang berminyak.'
    return 'Maaf, coba tanyakan lagi atau upload foto sampah untuk analisis.'
