from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / ".ui_walkthrough_frames"
OUTPUT = ROOT / "web_ui_walkthrough.mp4"
W, H = 1600, 900
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def f(path, size): return ImageFont.truetype(path, size)

def text(draw, xy, value, size=16, fill="#17231f", bold=False):
    draw.text(xy, value, font=f(BOLD if bold else FONT, size), fill=fill)

def base(active):
    im = Image.new("RGB", (W, H), "#f7f8f4")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, H), fill="#163b35")
    text(d, (38, 42), "NORTEX", 25, "#e9f4ee", True)
    text(d, (38, 75), "Travel expense control", 13, "#a8c8bd")
    for y, label in [(150,"Overview"),(198,"Expenses"),(246,"Approvals"),(294,"Evidence")]:
        selected = label.lower() == active
        d.rounded_rectangle((25, y, 230, y+38), 6, fill="#286359" if selected else "#163b35")
        text(d, (43, y+9), label, 16, "#ffffff" if selected else "#b8d1c8", selected)
    text(d, (38, 810), "Sample trip workspace", 12, "#a8c8bd")
    text(d, (38, 832), "NX-4471 · TRQ-2026-0000", 12, "#a8c8bd")
    return im, d

def card(d, x, y, w, h, label, value):
    d.rounded_rectangle((x,y,x+w,y+h), 7, fill="#ffffff", outline="#dfe7e2", width=2)
    text(d,(x+18,y+15),label,13,"#68756f")
    text(d,(x+18,y+45),value,25,"#17231f",True)

def header(d, eyebrow, title, subtitle):
    text(d,(310,52),eyebrow.upper(),12,"#087f72",True)
    text(d,(310,79),title,34,"#17231f",True)
    text(d,(310,126),subtitle,16,"#68756f")
    d.rounded_rectangle((1250,55,1518,101),7,fill="#087f72")
    text(d,(1280,69),"↓  Download completed form",14,"#ffffff",True)

def table_header(d, x, y, labels, widths):
    cur=x
    for label,width in zip(labels,widths):
        text(d,(cur,y),label.upper(),11,"#68756f",True); cur += width
    d.line((x,y+25,x+sum(widths),y+25),fill="#dfe7e2",width=2)

def slide_overview():
    im,d=base("overview"); header(d,"Claim workspace","Travel expense review","One place to verify the trip, policy decision, and approval state.")
    card(d,310,190,270,115,"Net reimbursable claim","INR 22,879.04")
    card(d,600,190,270,115,"Amount payable","INR 2,879.04")
    card(d,890,190,270,115,"Disallowed expenses","INR 4,205.00")
    card(d,1180,190,270,115,"Advance drawn","INR 20,000.00")
    d.rounded_rectangle((310,335,930,625),7,fill="#fff",outline="#dfe7e2",width=2); text(d,(335,360),"Claim overview",19,"#17231f",True)
    facts=[("Employee","Chaitanya Reddy · NX-4471"),("Travel request","TRQ-2026-0000"),("Destination","Bengaluru"),("Travel dates","16 Jun 2026 - 20 Jun 2026"),("Category","Domestic - Tier 1"),("Purpose","Customer meeting + site visit")]
    for i,(a,b) in enumerate(facts):
        x=335+(i%2)*290; y=410+(i//2)*65; text(d,(x,y),a,12,"#68756f"); text(d,(x,y+22),b,15,"#17231f",True)
    d.rounded_rectangle((950,335,1518,625),7,fill="#fff",outline="#dfe7e2",width=2); text(d,(975,360),"Settlement",19,"#17231f",True)
    for i,(a,b) in enumerate([("Employee-paid claim","INR 22,879.04"),("Less: advance","INR 20,000.00"),("Payable to employee","INR 2,879.04")]):
        y=415+i*55; text(d,(975,y),a,14,"#68756f"); text(d,(1350,y),b,14,"#17231f",True); d.line((975,y+30,1490,y+30),fill="#dfe7e2")
    text(d,(310,680),"POLICY FINDINGS",12,"#087f72",True)
    text(d,(310,710),"✓ Local transport is reimbursable on actuals and supported by Uber receipts.",15,"#52635c")
    text(d,(310,745),"! Hotel extras and unsupported business entertainment are disallowed.",15,"#a05b10")
    return im

def slide_expenses():
    im,d=base("expenses"); header(d,"Expense review","Travel & transportation","Extracted from the email packet and matched to supporting evidence.")
    d.rounded_rectangle((310,190,1518,530),7,fill="#fff",outline="#dfe7e2",width=2)
    widths=[150,390,100,120,150,200]; table_header(d,335,220,["Date / time","Route","Mode","Paid by","Amount","Proof"],widths)
    rows=[("16-Jun-2026\n05:20 AM","Baner, Pune → Pune International Airport","Uber","Employee","INR 1,415.02","06_uber_receipt_1.eml"),("16-Jun-2026\n09:52 AM","Kempegowda Airport → Keys Prime Hotel","Uber","Employee","INR 743.00","07_uber_receipt_2.eml"),("17-Jun-2026\n07:35 PM","Vertex Technologies → Keys Prime Hotel","Uber","Employee","INR 172.00","09_uber_receipt_3.eml"),("20-Jun-2026\n09:05 PM","Pune International Airport → Baner","Uber","Employee","INR 1,229.02","15_return_cab.eml")]
    for i,row in enumerate(rows):
        y=270+i*58; cur=335
        for val,width in zip(row,widths): text(d,(cur,y),val,13,"#17231f",val.startswith("INR")); cur+=width
        d.line((335,y+39,1490,y+39),fill="#edf1ee")
    d.rounded_rectangle((310,565,870,760),7,fill="#fff",outline="#dfe7e2",width=2); text(d,(335,590),"Lodging",19,"#17231f",True); text(d,(335,635),"Keys Prime Hotel",15,"#17231f",True); text(d,(335,670),"Reimbursable",12,"#68756f"); text(d,(335,692),"INR 19,320.00",18,"#17231f",True); text(d,(650,670),"Within policy",13,"#087f72",True)
    d.rounded_rectangle((895,565,1518,760),7,fill="#fff",outline="#dfe7e2",width=2); text(d,(920,590),"Disallowed expenses",19,"#17231f",True); text(d,(920,640),"Hotel extras + dinner",14,"#68756f"); text(d,(920,672),"INR 4,205.00",20,"#a05b10",True); text(d,(920,710),"Flagged with policy reasons",13,"#a05b10")
    return im

def slide_approvals(stage="pending"):
    im,d=base("approvals"); header(d,"Workflow","Approval & finance processing","Each reviewer must act before the next stage becomes available.")
    d.rounded_rectangle((310,190,1518,585),7,fill="#fff",outline="#dfe7e2",width=2); table_header(d,335,220,["Level","Role / owner","Decision","Date","Remarks"],[80,330,150,150,390])
    decisions=[("1","Employee (submitted by)","Submitted","20-Jun-2026","Claim submitted within policy deadline","approved"),("2","Reporting Manager","Pending","—","Awaiting review","pending"),("3","Head of Department","Pending","—","Awaiting reporting manager approval","pending"),("4","Finance - verification","Pending","—","Awaiting HOD approval","pending"),("5","Finance - payment released","Pending","—","Awaiting finance verification","pending")]
    if stage=="manager-approved": decisions[1]= ("2","Reporting Manager","Approved","09-Sep-2026","Approved after expense and evidence review","approved"); decisions[2]= ("3","Head of Department","Pending","—","Awaiting review","pending")
    for i,row in enumerate(decisions):
        y=270+i*58; cur=335
        for val,width in zip(row[:5],[80,330,150,150,390]):
            color="#087f72" if val in {"Approved","Submitted"} else "#a05b10" if val=="Pending" else "#17231f"; text(d,(cur,y),val,13,color,val in {"Approved","Pending"}); cur+=width
        d.line((335,y+39,1490,y+39),fill="#edf1ee")
    d.rounded_rectangle((310,620,1518,775),7,fill="#fff",outline="#dfe7e2",width=2)
    if stage=="pending":
        text(d,(335,650),"REVIEWER ACTION · REPORTING MANAGER",12,"#087f72",True); text(d,(335,680),"Suresh Iyer · next action available",16,"#17231f",True); text(d,(335,710),"Review expenses and evidence, then choose an action.",14,"#68756f"); d.rounded_rectangle((1220,680,1395,728),6,fill="#087f72"); text(d,(1252,695),"Approve / verify",13,"#fff",True); d.rounded_rectangle((1410,680,1490,728),6,fill="#f9e4df"); text(d,(1428,695),"Reject",13,"#a43f31",True)
    else:
        text(d,(335,650),"NEXT ACTION UNLOCKED",12,"#087f72",True); text(d,(335,680),"Head of Department · Meera Krishnan",16,"#17231f",True); text(d,(335,710),"Manager approval is now visible to the employee and HOD reviewer.",14,"#68756f")
    return im

def slide_evidence():
    im,d=base("evidence"); header(d,"Audit trail","Evidence packet","Source emails used to reconstruct the claim and populate the workbook.")
    d.rounded_rectangle((310,190,1518,650),7,fill="#fff",outline="#dfe7e2",width=2); table_header(d,335,220,["#","Source file","Origin","Status"],[70,470,350,180])
    files=["01_travel_approval_request.eml","02_travel_approval_granted.eml","04_flight_eticket.eml","06_uber_receipt_1.eml","12_hotel_invoice.eml","15_return_cab.eml"]
    for i,name in enumerate(files):
        y=270+i*55; text(d,(335,y),str(i+1),13,"#68756f"); text(d,(405,y),name,14,"#17231f",True); text(d,(875,y),"Parsed from sample inbox",13,"#68756f"); text(d,(1300,y),"Used",13,"#087f72",True); d.line((335,y+35,1490,y+35),fill="#edf1ee")
    d.rounded_rectangle((310,690,1518,775),7,fill="#dff2ed",outline="#b8dfd4",width=2); text(d,(335,715),"Receipt images: hotel_invoice_1188.png · dinner_bill_18jun.png",15,"#087f72",True); text(d,(335,744),"OCR when available, email text fallback otherwise.",13,"#52635c")
    return im

def main():
    FRAMES.mkdir(exist_ok=True)
    slides=[slide_overview(),slide_expenses(),slide_approvals(),slide_approvals("manager-approved"),slide_evidence()]
    for i,im in enumerate(slides): im.save(FRAMES/f"ui-{i:02d}.png")
    # 8 seconds per screen; 40 seconds total, intentionally demo-paced.
    subprocess.run(["ffmpeg","-y","-framerate","1/8","-i",str(FRAMES/"ui-%02d.png"),"-c:v","libx264","-pix_fmt","yuv420p",str(OUTPUT)],check=True,capture_output=True)
    print(OUTPUT)

if __name__ == "__main__": main()
