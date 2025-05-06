
import datetime
import logging
import os
import pytz
from dotenv import load_dotenv

from supabase import create_client, Client
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from telegram_pdf import CreatePDF

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()

url = os.getenv('DB_URL')
key = os.getenv('DB_KEY')
supabase = create_client(url, key)

meses = {
    "2025-01": "Janeiro",
    "2025-02": "Fevereiro",
    "2025-03": "Marco",
    "2025-04": "Abril",
    "2025-05": "Maio",
    "2025-06": "Junho",
    "2025-07": "Julho",
    "2025-08": "Agosto",
    "2025-09": "Setembro",
    "2025-10": "Outubro",
    "2025-11": "Novembro",
    "2025-12": "Dezembro"
}

registrando = False
editando = False
informando_horario = False
informando_laboratorio = False
informando_atividade = False
laboratorio = horario = atividade = quantidade = ""
editando_id = None


async def help_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use /lembrete para iniciar o envio diário de lembretes.\n"
        "Use /stop para cancelar o envio diário de lembretes.\n"
        "Use /registrar para registrar seus horários.\n"
        "Use /dados (nome,orientador,modalidade_da_bolsa) para configurar seus dados.\n"
        "Use /pdf para gerar relatório PDF.\n"
        "Use /registros para ver todos os registros e seus IDs.\n"
        "Use /editar (id) para editar um registro.\n"
        "Use /help para visualizar os comandos.",
    )


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"Registra tuas hora guri!")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def has_job(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.job_queue.get_jobs_by_name(name):
        return False

    return True


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id

    if has_job(str(chat_id), context):
        await update.effective_message.reply_text("Lembretes já ativados")
        return

    time = datetime.time(
        hour=20,
        tzinfo=pytz.timezone('Brazil/East'),
    )

    context.job_queue.run_daily(
        alarm,
        time=time,
        days=(1, 2, 3, 4, 5),
        chat_id=chat_id,
        name=str(chat_id),
    )

    await update.effective_message.reply_text("Envio automático de lembretes ativado (seg - sex 20h).")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Envio de lembretes cancelado!" if job_removed else "O envio de lembretes já está desativado."
    await update.message.reply_text(text)


async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Informe o laboratório: ")
    global informando_laboratorio, registrando
    informando_laboratorio = True
    registrando = True


async def informar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Informe o horário trabalhado (xx:xx,xx:xx): ")
    global informando_laboratorio, informando_horario
    informando_horario = True
    informando_laboratorio = False


async def informar_atividade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Informe a atividade realizada: ")
    global informando_atividade, informando_horario
    informando_horario = False
    informando_atividade = True


async def dados(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    try:
        print(context.args)
        chat_id = update.message.chat_id
        parametros = " ".join(context.args).split(",")

        nome = parametros[0]
        orientador = parametros[1]
        modalidade = parametros[2]

        try:
            response = (
                supabase.table("usuario")
                .insert({"chat_id": str(chat_id),"nome": nome, "orientador": orientador, "modalidade": modalidade})
                .execute()
            )
        except:
            response = (
                supabase.table("usuario")
                .update({"nome": nome, "orientador": orientador,
                         "modalidade": modalidade})
                .eq("chat_id", str(chat_id))
                .execute()
            )

        print(nome, orientador, modalidade, sep=" | ")

        await update.message.reply_text("Dados informados com sucesso")
    except IndexError:
        await update.message.reply_text("Informe os dados após o comando (/dados (nome,orientador,modalidade_da_bolsa))")


async def generate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Gerando PDF")
    global supabase

    data = str(datetime.datetime.now().date())

    try:
        mes = context.args[0]

    except IndexError:
        mes = "-".join(data.split("-")[0:2])

    chat_id = update.message.chat_id


    response = (
        supabase.table("relatorio")
        .select("*").eq("chat_id", str(chat_id)).eq("mes", mes)
        .order("dia", desc=False)
        .execute()
    )

    laboratorios = {
        "labs": [],
        "salas": []
    }

    tabela = [
        ["Dia", "Horário", "Atividade", "Carga Horária"],
    ]

    carga_horaria = datetime.timedelta()

    for dado in response.data:
        print(dado)
        if "lab" in dado["sala"].lower():
            laboratorios["labs"].append(dado["sala"])
        if "sala" in dado["sala"].lower():
            laboratorios["salas"].append(dado["sala"])

        time = datetime.datetime.strptime(dado["tempo"], "%H:%M:%S")

        carga_horaria += datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)

        tabela.append([dado['dia'], dado['horas'], dado['atividade'], dado['tempo']])


    tabela.append(["", "", "Carga horária total:", carga_horaria])

    laboratorios["labs"] = set(laboratorios["labs"])
    laboratorios["salas"] = set(laboratorios["salas"])

    response = (
        supabase.table("usuario")
        .select("*").eq("chat_id", str(chat_id))
        .execute()
    )

    print(response.data)
    dados = response.data[0]
    nome = dados["nome"]
    orientador = dados["orientador"]
    modalidade = dados["modalidade"]

    pdf = CreatePDF(
        f"Relatorio {meses[mes]} {nome}.pdf",
        "Relatorio",
        nome,
        orientador,
        modalidade,
        laboratorios,
        tabela
    )

    path = pdf.get_pdf()

    await update.message.reply_document(path)

    try:
        os.remove(path)
    except FileNotFoundError:
        return


async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    global registrando, informando_atividade, laboratorio, horario, atividade, quantidade, supabase, editando, editando_id

    chat_id = update.message.chat_id

    if editando:
        mensagem = update.message.text.split("|")
        try:
            data = mensagem[0].split("-")

            int(data[0])
            int(data[1])
            int(data[2])

            if len(data) != 3 or len(data[0]) != 4 or len(data[1]) != 2 or len(data[2]) != 2:
                await update.message.reply_text("A data foi escrita no formato errado.")
                return


        except Exception as e:
            await update.message.reply_text("A data foi escrita no formato errado.")
            return

        try:
            horario = mensagem[2]
            horario = horario.split(" - ")
            hora1 = horario[0].split(":")
            hora2 = horario[1].split(":")

            int(hora1[0])
            int(hora1[1])

            int(hora2[0])
            int(hora2[1])

            hora1 = datetime.timedelta(hours=int(hora1[0]), minutes=int(hora1[1]))
            hora2 = datetime.timedelta(hours=int(hora2[0]), minutes=int(hora2[1]))

            quantidade = str(hora2 - hora1)

        except:
            await update.message.reply_text("O horário foi escrito no formato errado. Informe novamente.")
            return

        response = (
            supabase.table("relatorio")
            .update({
                "dia": mensagem[0],
                "sala": mensagem[1],
                "horas": mensagem[2],
                "atividade": mensagem[3],
                "tempo": quantidade,
                "mes": "-".join(mensagem[0].split("-")[0:2]),
            })
            .eq("chat_id", str(chat_id)).eq("id", editando_id)
            .execute()
        )

        await update.message.reply_text("Registro atualizado com sucesso")


    if not registrando:
        return

    if informando_laboratorio:
        laboratorio = update.message.text
        await informar_horario(update, context)

    elif informando_horario:
        try:
            horario = update.message.text
            horario = horario.split(",")
            hora1 = horario[0].split(":")
            hora2 = horario[1].split(":")

            int(hora1[0])
            int(hora1[1])

            int(hora2[0])
            int(hora2[1])

            hora1 = datetime.timedelta(hours=int(hora1[0]), minutes=int(hora1[1]))
            hora2 = datetime.timedelta(hours=int(hora2[0]), minutes=int(hora2[1]))

            quantidade = hora2 - hora1

            horario = " - ".join(horario)

            await informar_atividade(update, context)
        except:
            await update.message.reply_text("O texto foi escrito no formato errado. Informe novamente.")

    elif informando_atividade:
        informando_atividade = False
        registrando = False
        atividade = update.message.text
        print(datetime.datetime.now().date(), laboratorio, horario, atividade, quantidade, sep=" | ")

        data = str(datetime.datetime.now().date())

        response = (
            supabase.table("relatorio")
            .insert({
                "chat_id": chat_id,
                "dia":data,
                "sala": laboratorio,
                "horas": horario,
                "atividade": atividade,
                "tempo": str(quantidade),
                "mes": "-".join(data.split("-")[0:2]),
            })
            .execute()
        )

        await update.message.reply_text("Dados informados com sucesso.")

        laboratorio = horario = atividade = ""


async def mostrar_registros(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    global supabase

    chat_id = update.message.chat_id
    data = str(datetime.datetime.now().date())

    try:
        mes = context.args[0]

    except IndexError:
        mes = "-".join(data.split("-")[0:2])

    response = (
        supabase.table("relatorio")
        .select("*")
        .eq("chat_id", str(chat_id)).eq("mes", mes)
        .order("dia", desc=False)
        .execute()
    )

    msg = ""

    for registro in response.data:
        msg += f"[{registro["id"]}] {registro["dia"]}|{registro['sala']}|{registro['horas']}|{registro['atividade']}\n"

    await update.message.reply_text(msg)


async def editar_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global supabase, editando, editando_id
    chat_id = update.message.chat_id

    registro_id = None

    try:
        registro_id = context.args[0]

    except IndexError:
        await update.message.reply_text("Informe o id do registro.")
        return

    response = (
        supabase.table("relatorio")
        .select("*")
        .eq("chat_id", str(chat_id)).eq("id", registro_id)
        .execute()
    )

    editando = True
    editando_id = registro_id

    response = response.data[0]

    await update.message.reply_text(f"Registro atual:\n"
                                    f"[Dia] | [Sala] | [Horas] | [Atividade]")

    await update.message.reply_text(f"{response["dia"]}|{response['sala']}|{response['horas']}|{response['atividade']}")





def main() -> None:

    application = Application.builder().token(os.getenv('TELEGRAM_KEY')).build()

    application.add_handler(CommandHandler(["start", "help", "h"], help_text))
    application.add_handler(CommandHandler("dados", dados))
    application.add_handler(CommandHandler("lembrete", set_timer))
    application.add_handler(CommandHandler("editar", editar_registro))
    application.add_handler(CommandHandler("PDF", generate_pdf))
    application.add_handler(CommandHandler("registros", mostrar_registros))
    application.add_handler(CommandHandler("stop", unset))
    application.add_handler(CommandHandler("registrar", registrar))
    application.add_handler(MessageHandler(filters.ALL, handle_messages))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()