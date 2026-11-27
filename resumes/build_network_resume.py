from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

NAVY = colors.HexColor("#1F3A5F")
F, FB = "Helvetica", "Helvetica-Bold"
name = ParagraphStyle("n", fontName=FB, fontSize=22, leading=26, alignment=TA_CENTER, textColor=NAVY)
role = ParagraphStyle("r", fontName=FB, fontSize=10.5, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#333333"))
contact = ParagraphStyle("c", fontName=F, fontSize=8.3, leading=12, alignment=TA_CENTER)
h = ParagraphStyle("h", fontName=FB, fontSize=11, leading=14, textColor=NAVY, spaceBefore=9, spaceAfter=2)
body = ParagraphStyle("b", fontName=F, fontSize=9, leading=12, alignment=TA_JUSTIFY)
bul = ParagraphStyle("bl", parent=body, alignment=0)
proj = ParagraphStyle("p", fontName=F, fontSize=9, leading=12, spaceBefore=5, spaceAfter=1)

def sec(t):
    return [Paragraph(t.upper(), h), HRFlowable(width="100%", thickness=0.8, color=NAVY, spaceAfter=4)]
def bullets(items):
    return ListFlowable([ListItem(Paragraph(i, bul), leftIndent=10, bulletColor=NAVY) for i in items],
        bulletType="bullet", start="•", bulletFontSize=7, leftIndent=10, bulletOffsetY=-0.5)
def pr(title, tools):
    return Paragraph(f"<b>{title}</b> | <i>{tools}</i>", proj)

s = []
s += [Paragraph("ANURAG RAJKUMAR TIWARI", name),
      Paragraph("Network Engineer | Networking and Network Security", role),
      Spacer(1,5),
      Paragraph("+91-9653235350 &nbsp;|&nbsp; anuragtiwari.dev1@gmail.com &nbsp;|&nbsp; "
                "<link href='https://github.com/anurag123-at' color='#1F3A5F'>github.com/anurag123-at</link> &nbsp;|&nbsp; "
                "<link href='https://linkedin.com/in/anuragtiwari-dev' color='#1F3A5F'>linkedin.com/in/anuragtiwari-dev</link>", contact)]

s += sec("Summary")
s.append(Paragraph("Final-year B.E. Computer Science student (CGPA 9.20/10) with a strong base in computer networks, IP addressing and TCP/IP, "
  "backed by a networking certification and hands-on practice with ping, Nmap and packet sniffing. Cybersecurity background gives a security-aware "
  "view of network design and troubleshooting. Comfortable with Linux, Python and Bash scripting for network automation, and with AWS networking basics.", body))

s += sec("Technical Skills")
rows = [
 ("Networking", "OSI and TCP/IP models, IP addressing and subnetting, TCP/UDP, DNS, DHCP, routing and switching concepts"),
 ("Network Tools", "ping, Nmap, Wireshark (packet sniffing and traffic analysis), network mapping and port scanning"),
 ("Network Security", "Vulnerability assessment, Nessus, Metasploit, Burp Suite, cryptography, network security fundamentals"),
 ("Cloud", "AWS: EC2, Security Groups, IAM, S3"),
 ("Systems", "Linux, Windows, Bash scripting, Python (automation), SQL, Git, GitHub"),
]
t = Table([[Paragraph(f"<b>{a}</b>", body), Paragraph(b, body)] for a,b in rows], colWidths=[34*mm, None])
t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                       ("TOPPADDING",(0,0),(-1,-1),1.5),("BOTTOMPADDING",(0,0),(-1,-1),1.5)]))
s.append(t)

s += sec("Experience")
s.append(Paragraph("<b>AI Engineer Intern</b>, CMS, Ghansoli <font color='#555555'>(October 2026 – Present)</font>", proj))
s.append(bullets([
 "Annotated images and generated labelled datasets for computer-vision model training.",
 "Trained a YOLO model to auto-annotate new data.",
 "Wrote Python scripts to rename, sort and split labelled files, and to remove duplicates, empty files and images with no matching .txt label."]))
s.append(Paragraph("<b>Python Trainee</b>, Smartbyte Education <font color='#555555'>(8 months)</font>", proj))
s.append(bullets(["Hands-on Python training covering core programming, problem solving and scripting."]))

s += sec("Projects")
s.append(pr("Vulnerability Assessment Lab (Self-Directed)", "Nmap, Metasploit, Wireshark, virtual machines"))
s.append(bullets([
 "Configured virtual lab environments to practice Nmap network mapping, port scanning and Metasploit exploitation.",
 "Documented findings and remediation steps for identified vulnerabilities, mirroring real-world VAPT reporting."]))
s.append(pr("AI-Powered Cloud Penetration Testing Framework", "Python, AI workflows, cloud security"))
s.append(bullets([
 "Built an automated framework for reconnaissance and vulnerability assessment in cloud environments.",
 "Automated repetitive scanning tasks with Python and generated security audit reports."]))

s += sec("Education and Certifications")
s.append(bullets([
 "<b>B.E. Computer Science</b>, Terna Engineering College, Mumbai University, 2023–2027, CGPA 9.20/10; HSC 2023: 85%; SSC 2021: 91%",
 "<b>Networking Certification</b>, TechnoHacks Solutions (2 months)",
 "Coursework: Computer Networks, Cryptography and Network Security, Ethical Hacking, Cloud Computing, Operating Systems"]))

doc = SimpleDocTemplate("/tmp/r/Anurag_Tiwari_Network_Engineer_Resume.pdf", pagesize=A4,
    leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=10*mm,
    title="Anurag Rajkumar Tiwari - Network Engineer Resume", author="Anurag Rajkumar Tiwari")
doc.build(s)
from pypdf import PdfReader
print(len(PdfReader("/tmp/r/Anurag_Tiwari_Network_Engineer_Resume.pdf").pages))
