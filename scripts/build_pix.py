#!/usr/bin/env python3
"""
Gera o payload oficial Pix BR Code (EMVCo) e o QR Code em formato SVG.
Este script lê as variáveis de ambiente (Secrets) configuradas no GitHub:
- PIX_KEY (ex: +5561992454063 ou 61992454063)
- PIX_NAME (ex: BACAR NHAGA)
- PIX_CITY (ex: BRASILIA)
- PIX_KEY_FORMATTED (ex: (61) 99245-4063)
"""
import os
import re
import sys

def format_tlv(tag: str, value: str) -> str:
    """Formata no padrão Tag-Length-Value (EMVCo)."""
    return f"{tag}{len(value):02d}{value}"

def calculate_crc16(payload: str) -> str:
    """Calcula o checksum CRC16-CCITT (0xFFFF polinômio 0x1021)."""
    crc = 0xFFFF
    for char in payload.encode('ascii'):
        crc ^= (char << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def generate_pix_payload(pix_key: str, name: str, city: str) -> str:
    # 00: Payload Format Indicator
    payload = format_tlv("00", "01")
    # 01: Point of Initiation Method (12 = Estático/Reutilizável ou Dinâmico)
    payload += format_tlv("01", "12")
    # 26: Merchant Account Information - Pix
    mai = format_tlv("00", "br.gov.bcb.pix")
    mai += format_tlv("01", pix_key)
    payload += format_tlv("26", mai)
    # 52: Merchant Category Code
    payload += format_tlv("52", "0000")
    # 53: Transaction Currency (986 = BRL)
    payload += format_tlv("53", "986")
    # 58: Country Code
    payload += format_tlv("58", "BR")
    # 59: Merchant Name (máx 25 carac)
    payload += format_tlv("59", name[:25])
    # 60: Merchant City (máx 15 carac)
    payload += format_tlv("60", city[:15])
    # 62: Additional Data Field Template (TxID = ***)
    payload += format_tlv("62", format_tlv("05", "***"))
    # 63: CRC16 template
    payload_to_crc = payload + "6304"
    crc = calculate_crc16(payload_to_crc)
    return payload_to_crc + crc

def generate_qr_svg(payload: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(payload, image_factory=factory, box_size=10, border=1)
        svg_bytes = img.to_string()
        svg_str = svg_bytes.decode('utf-8') if isinstance(svg_bytes, bytes) else str(svg_bytes)
        # Extrai apenas o elemento <svg ...>...</svg>
        match = re.search(r'(<svg.*?</svg>)', svg_str, re.DOTALL)
        if match:
            svg_content = match.group(1)
            # Ajusta classes para Tailwind
            svg_content = re.sub(r'width=".*?"', 'class="w-32 h-32 sm:w-36 sm:h-36 text-on-surface"', svg_content, count=1)
            svg_content = re.sub(r'height=".*?"', '', svg_content, count=1)
            return svg_content
    except ImportError:
        print("Aviso: biblioteca 'qrcode' não encontrada. Mantendo SVG existente.")
    return None

def main():
    pix_key = os.environ.get("PIX_KEY", "+5561992454063").strip()
    pix_name = os.environ.get("PIX_NAME", "BACAR NHAGA").strip()
    pix_city = os.environ.get("PIX_CITY", "BRASILIA").strip()
    pix_formatted = os.environ.get("PIX_KEY_FORMATTED", "(61) 99245-4063").strip()

    payload = generate_pix_payload(pix_key, pix_name, pix_city)
    print(f"Generated Pix Payload: {payload}")

    template_path = os.environ.get("TEMPLATE_HTML", "index.html")
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found.")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Injeta a constante PIX_PAYLOAD
    html = re.sub(
        r'const PIX_PAYLOAD = ".*?";',
        f'const PIX_PAYLOAD = "{payload}";',
        html
    )

    # Injeta a chave formatada no texto visual
    html = re.sub(
        r'id="pixFormattedKey">.*?</div>',
        f'id="pixFormattedKey">{pix_formatted}</div>',
        html
    )

    # Injeta QR Code SVG se a lib estiver disponível
    new_svg = generate_qr_svg(payload)
    if new_svg:
        html = re.sub(
            r'<div class="bg-surface-container-lowest p-2\.5 rounded-lg shadow-inner border border-outline-variant/20 flex items-center justify-center">.*?</div>',
            f'<div class="bg-surface-container-lowest p-2.5 rounded-lg shadow-inner border border-outline-variant/20 flex items-center justify-center" id="qrContainer">\n            {new_svg}\n          </div>',
            html,
            flags=re.DOTALL
        )

    output_path = os.environ.get("OUTPUT_HTML", "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Successfully injected Pix payload and updated {output_path}")

if __name__ == "__main__":
    main()
