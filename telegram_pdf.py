from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.platypus.tables import Table, TableStyle


class CreatePDF:

	def __init__(self, filename, document_title, nome, orientador, modalidade, salas, tabela):

		self.filename = filename
		self.document_title = document_title

		self.nome = nome
		self.orientador = orientador
		self.modalidade = modalidade
		self.salas = salas
		self.tabela = tabela

	def get_pdf(self):
		image1 = './images/ufn.png'
		image2 = './images/nano.png'

		doc = SimpleDocTemplate(self.filename,
								title=self.document_title,
								pagesize=A4,
								rightMargin=90,
								leftMargin=90,
								topMargin=20,
								bottomMargin=18)

		flowables = []

		chart_style = TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
								  ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
								  ('VALIGN', (0, 0), (-1, -1), 'CENTER')])

		spacing = 7.3

		cabecalho = Table([[
			Image(image1, width=100, height=50, hAlign='LEFT'),
			Image(image2, width=150, height=50, hAlign='RIGHT')
		]], colWidths=[spacing * cm, spacing * cm], style=chart_style)

		flowables.append(cabecalho)

		labs = ""

		for lab in self.salas["labs"]:
			labs += lab + ", "

		for sala in self.salas["salas"]:
			labs += sala + ", "

		text = (f"Bolsista: {self.nome}<br/>"
				f"Orientador: {self.orientador}<br/>"
				f"Bolsa: CAPES - Modalidade {self.modalidade}<br/>"
				f"Laboratório / Sala: {labs.rstrip(", ")}")

		para = Paragraph(text, style=ParagraphStyle(name="Infos", fontName="Times-Bold", fontSize=10))
		flowables.append(para)

		t = Table(data=self.tabela, colWidths=[None, None, 180, None])

		t.setStyle(TableStyle(
			[
				('ALIGN', (0, 0), (-1, -1), 'LEFT'),
				('ALIGN', (-2, -1), (-2, -1), 'RIGHT'),
				('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
				('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
				('BACKGROUND', (0, 0), (-1, 0), colors.gray),
				('BACKGROUND', (0, -1), (-1, -1), colors.green),
				('FONT', (0, 0), (-1, -1), "Times-Roman"),
				('FONT', (0, 0), (-1, 0), "Times-Bold"),
				('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
				('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
				('BOX', (0, 0), (-1, -1), 0.25, colors.black)
			]))

		t.wrap(0, 0)
		flowables.append(Spacer(1, 0.5 * cm))
		flowables.append(t)

		flowables.append(Spacer(1, 2 * cm))

		chart_style = TableStyle([
			('ALIGN', (0, 0), (-1, -1), 'CENTER'),
			('LINEABOVE', (0, 0), (0, 0), 0.5, colors.black),
			('LINEABOVE', (-1, -1), (-1, -1), 0.5, colors.black),
			('LEFTPADDING', (0, 0), (-1, -1), 10),
			('RIGHTPADDING', (0, 0), (-1, -1), 10),
		])
		t = Table(data=[["Aluno", Spacer(1 * cm, 1), "Orientador"]], colWidths=[5 * cm, 5 * cm, 5 * cm],
				  style=chart_style)
		flowables.append(t)

		doc.build(flowables)

		return self.filename