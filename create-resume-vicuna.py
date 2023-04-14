import os
import re
import hashlib
import json
import locale
import fitz
import requests
from datetime import datetime
from tqdm.auto import tqdm

def process_folder():

    # Crear una ventana de selección de carpeta
    folder_path = "./pdf"
    
    #Procesar los archivos PDF en la carpeta seleccionada
    if folder_path:

        pdf_files = [f.path for f in os.scandir(folder_path) if f.name.endswith('.pdf')]

        try:

            with tqdm(total=len(pdf_files), desc="Procesando archivos") as pbar:
                for pdf_file in pdf_files:
                    process_pdf(pdf_file)
                    pbar.update()

            return True

        except Exception as e:
            print(f"Se produjo un error: {e}")


def process_pdf(pdf_file):

    try:

        text = ''

        with fitz.open(pdf_file) as doc:

            for page in doc:
                blocks = page.get_text("blocks")
                # Ordenar los bloques por posición en la página (de arriba a abajo y de izquierda a derecha)
                blocks.sort(key=lambda block: (block[1], block[0]))
                # Concatenar el texto de cada bloque
                for block in blocks:
                    # Dividir el texto del bloque en líneas
                    lines = block[4].splitlines()
                    # Eliminar espacios en blanco al final de cada línea y unir las líneas
                    block_text = ' '.join(line.rstrip() for line in lines)
                    text += '\n'
                    # Agregar el texto del bloque al texto final
                    text += block_text
                    # Agregar un salto de línea después del texto del bloque
                    text += '\n'
            
        text = re.sub(r'<image:.*?>', '', text)
        text = re.sub(r"D\.L\.: PM 469-1983 - ISSN: 2254-1233", "", text)

        # Buscar la URL del documento
        match = re.search(r"(https?://www\.caib\.es/eboibfront/pdf/(es|ca)/[^'\"\s]+)", text)

        if match:
            #Eliminar del texto todas las apariciones de la URL
            text = re.sub(r"(https?://www\.caib\.es/eboibfront/pdf/(es|ca)/[^'\"\s]+)", "", text)

            # Generar metadatos
            url = match.group(1)
            url = re.sub(r"http://", "https://", url)

            language = "castellano" if match.group(2) == "es" else "catalan"

            if language == "catalan":
                return

            m = hashlib.md5() 
            m.update(url.encode('utf-8'))
            uid = m.hexdigest()[:12]
            
        else:
            print("No se encontró ninguna URL en el texto.")

        print(f"Procesando {pdf_file}")
        
        lines = text.split("\n")
        title = lines[13]
        content = lines[14:]
        content = "\n".join(content)

        server = "127.0.0.1"

        params = {
            'max_new_tokens': 200,
            'do_sample': True,
            'temperature': 0.1,
            'top_p': 0.73,
            'typical_p': 1,
            'repetition_penalty': 1.1,
            'encoder_repetition_penalty': 1.0,
            'top_k': 0,
            'min_length': 0,
            'no_repeat_ngram_size': 0,
            'num_beams': 1,
            'penalty_alpha': 0,
            'length_penalty': 1,
            'early_stopping': True,
            'num_return_sequences': 1,
            'seed': -1,
            'truncation_length': 1000,
            'add_bos_token': True,
            'custom_stopping_strings': ["### Human"],
            'ban_eos_token': False,
        }

        prompt = "### Human: Partiendo del siguiente texto:'" + content + ". \n' Su resumen breve es: " + title + ".\n Escribe un resumen más extenso con los aspectos más importantes Sigue estas reglas: 1º Escribe en español. 2º No escribas cantidades de dinero. 3º Nunca definas las siglas de una institución. 4º No empieces por la palabra 'resumen' --- ### Assistant:"
       
        payload = json.dumps([prompt, params])

        response = requests.post(f"http://{server}:7860/run/textgen", json={
            "data": [
                payload
            ]
        }).json()

        reply = response["data"][0]
        resume = reply.split(" --- ### Assistant:")[1]
        resume = re.sub(r"\s+", " ", resume).strip().lstrip()

        if not resume.endswith("."):
            resume = resume[:resume.rfind(".")+1]

        if resume.lower().startswith("resumen:"):
            resume = resume[8:].strip().lstrip()

        if resume.lower().startswith("resumen extenso:"):
            resume = resume[16:].strip().lstrip()

        num = ''
        date = ''
        page =  ''
        fascicle = ''
        section = ''

        metadata_regex = r"(?<!\S)https?:\/\/(?:www\.)?(?:boib\.caib\.es|(?:www\.)?caib\.es\/eboibfront\/)[^\/\s]*\/? *(?!\S)"   
        match = re.split(metadata_regex, text, maxsplit=1)

        if len(match) > 1:

            metadata, text = match[:2]
            
            if re.search(r"Núm\.", metadata) is None:
                metadata = ''      

        else:
            metadata = ''


        if len(metadata) > 1:

            num_regex = r'Núm\. (\d+)'
            date_regex = r'(\d+)\s+(?:d\'|de\s+)([a-zA-ZçÇ]+)\s+de\s+(\d+)'
            page_regex = r'P[àá]g\. (\d+)'
            section_regex = r'Sec\. ([IVXLCDM]+)'
            fascicle_regex = r'Fascicle (\d+)'

            num = re.search(num_regex, metadata).group(1) if re.search(num_regex, metadata) else ''
            date = re.search(date_regex, metadata).group() if re.search(date_regex, metadata) else ''
            page = re.search(page_regex, metadata).group(1) if re.search(page_regex, metadata) else ''
            section = re.search(section_regex, metadata).group(1) if re.search(section_regex, metadata) else ''
            fascicle = re.search(fascicle_regex, metadata).group(1) if re.search(fascicle_regex, metadata) else ''

            date = re.sub(r"[\xa0\n]", " ", date)

            if language == "castellano":
                locale.setlocale(locale.LC_TIME, "es_ES.utf8")
            elif language == "catalan":
                locale.setlocale(locale.LC_TIME, "ca_ES.utf8")

            if re.search(r"\d+ \w+'?\w+ de \d{4}", date):
                date = re.sub(r"d'", "de ", date)
            
            if re.search(r"març", date):
                date = re.sub(r"març", "marzo", date)
                locale.setlocale(locale.LC_TIME, "es_ES.utf8")

            if date != '':
                date_format = "%d de %B de %Y"
                date_obj = datetime.strptime(date, date_format)
                date = date_obj.strftime("%Y-%m-%d")

        match = re.search(r'/(\d+)$', url)

        if match:

            url_number = match.group(1)

            document = {
                "id": f"{uid}",
                "text": resume,
                "metadata": {
                    "source": "file",
                    "source_id": url_number,
                    "source_section": "resume",
                    "url": url,
                    "created_at": date,
                    "author": "boib",
                    "numero": num,
                    "pagina": page,
                    "seccion": section,
                    "fasciculo": fascicle,
                    "idioma": language
                }
            }

            try:
                json.loads(json.dumps(document, ensure_ascii=False))
            except Exception as e:
                print(f"Un JSON no está bien formateado: {url_number}")

                with open(f'./descartes/descartes.jsonl', 'a', encoding='utf-8') as f:
                    f.write(f'{url_number}' + '\n')

            with open(f'./dataset-finetuning-resume/dataset-finetuning-resume.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(document, ensure_ascii=False) + '\n')
        else: 
            print(f"No se encontró el número de documento en la URL {url}")

        return True 
                
    except Exception as e:
        print (f"date: {date} para la URL {url}")

        print(f"Se produjo un error al procesar el archivo PDF con {url}: {e}")
        return False

if __name__ == '__main__':

    if not os.path.exists('./dataset-finetuning-resume'):
        os.makedirs('./dataset-finetuning-resume')

    process_folder()
    
    input("Presione ENTER para salir...")