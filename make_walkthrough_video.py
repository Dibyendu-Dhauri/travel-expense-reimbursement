from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FRAME_DIR = ROOT / ".walkthrough_frames"
OUTPUT = ROOT / "project_walkthrough.mp4"

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
WIDTH, HEIGHT = 1600, 900

SLIDES = [
    ("NORTEX", "Travel Expense Reimbursement", "From inbox evidence to a policy-checked settlement workbook", "01"),
    ("THE PROBLEM", "Manual claim preparation", "Employees gather approval emails, bookings, receipts, and advances by hand.\nThe result is slow preparation, avoidable errors, and unclear follow-up status.", "02"),
    ("INPUT PACKET", "One trip, many evidence sources", "15 sample emails  /  employee master CSV  /  travel policy  /  receipt images  /  official Excel template", "03"),
    ("EXTRACTION", "Structured data from unstructured evidence", "Python email parser reads MIME bodies and attachments.\nOCR can read receipt images, with email text as a fallback.\nAmounts are extracted from labeled fields and duplicate receipts are ignored.", "04"),
    ("POLICY REVIEW", "Every amount gets a decision", "Lodging and local transport are reimbursable.\nCompany-paid flights are excluded.\nHotel extras and unsupported entertainment are flagged as disallowed.", "05"),
    ("REVIEW UI", "One workspace for the claim", "Overview shows the employee, trip, totals, policy findings, and settlement.\nExpenses and Evidence pages show the records behind each decision.", "06"),
    ("APPROVAL FLOW", "No automatic approvals", "Reporting Manager -> Head of Department -> Finance verification -> Payment release\nEach reviewer takes an action. The next stage stays locked until the current stage is complete.", "07"),
    ("OUTPUT", "A ready-to-review Excel form", "The generated workbook contains the travel request, expense settlement, proof references, policy totals, and current approval state.\nDownload it from the web UI at any time.", "08"),
    ("LIVE DEMO", "pack-copy.vercel.app", "Open the hosted application, review the claim, take approval actions, and download the completed form.\nSource: github.com/Dibyendu-Dhauri/travel-expense-reimbursement", "09"),
]


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if paragraph != text.split("\n")[-1]:
            lines.append("")
    return lines


def make_slide(index, eyebrow, title, body, number):
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f5f7f2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 360, HEIGHT), fill="#163b35")
    draw.rectangle((360, 0, WIDTH, 18), fill="#087f72")
    draw.text((72, 78), eyebrow, font=font(BOLD_PATH, 22), fill="#9dd2c0")
    draw.text((72, 132), number, font=font(BOLD_PATH, 108), fill="#e9f4ee")
    draw.text((72, 770), "NORTEX / CLAIM CONTROL", font=font(BOLD_PATH, 14), fill="#a8c8bd")
    draw.text((450, 150), title, font=font(BOLD_PATH, 60), fill="#17231f")
    body_font = font(FONT_PATH, 29)
    y = 285
    for line in wrap(draw, body, body_font, 980):
        draw.text((450, y), line, font=body_font, fill="#52635c")
        y += 48
    draw.line((450, 700, 1430, 700), fill="#dfe7e2", width=2)
    draw.text((450, 730), f"{index + 1:02d} / {len(SLIDES):02d}", font=font(BOLD_PATH, 16), fill="#087f72")
    return image


def main():
    FRAME_DIR.mkdir(exist_ok=True)
    for index, slide in enumerate(SLIDES):
        make_slide(index, *slide).save(FRAME_DIR / f"slide-{index:02d}.png")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "1/8", "-i", str(FRAME_DIR / "slide-%02d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "format=yuv420p", str(OUTPUT),
    ], check=True, capture_output=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
