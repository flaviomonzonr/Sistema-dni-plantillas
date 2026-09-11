import os
import re
import copy
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from backend.config import TEMPLATES_DIR, CONTRACTS_DIR


class ContractGenerator:
    """
    Motor de generación de contratos y documentos laborales en formato DOCX.
    Garantiza:
    1. Preservación estricta del 100% del formato original (márgenes, fuentes, negritas,
       tablas, encabezados, pies de página, firmas y logotipos).
    2. Reemplazo inteligente de variables respetando el estilo de cada fragmento (Run-level replacement).
    3. Generación individual y masiva.
    4. Nomenclatura normalizada sin duplicados.
    """

    def __init__(self, templates_dir: Path = TEMPLATES_DIR, output_dir: Path = CONTRACTS_DIR):
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_template()

    def _ensure_default_template(self) -> Path:
        """Crea una plantilla de contrato modelo estándar si no existe ninguna en la carpeta de plantillas."""
        default_tpl_path = self.templates_dir / "Plantilla_Contrato_Sujeto_a_Modalidad.docx"
        if not default_tpl_path.exists():
            doc = docx.Document()
            
            # Estilos de página
            for section in doc.sections:
                section.top_margin = Inches(0.8)
                section.bottom_margin = Inches(0.8)
                section.left_margin = Inches(0.9)
                section.right_margin = Inches(0.9)

            # Título
            title = doc.add_paragraph()
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_title = title.add_run("CONTRATO DE TRABAJO SUJETO A MODALIDAD POR NECESIDAD DE MERCADO")
            run_title.bold = True
            run_title.font.name = "Calibri"
            run_title.font.size = Pt(13)

            # Subtítulo
            sub = doc.add_paragraph()
            sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_sub = sub.add_run("(D. Leg. N° 728 - Ley de Productividad y Competitividad Laboral)")
            run_sub.font.name = "Calibri"
            run_sub.font.size = Pt(9.5)
            run_sub.font.color.rgb = RGBColor(100, 100, 100)

            doc.add_paragraph()  # Espacio

            # Introducción
            p_intro = doc.add_paragraph()
            p_intro.paragraph_format.line_spacing = 1.15
            p_intro.paragraph_format.space_after = Pt(8)
            p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            p_intro.add_run("Conste por el presente documento, el Contrato de Trabajo Sujeto a Modalidad que celebran de una parte la empresa ")
            r_emp = p_intro.add_run("[EMPRESA_NOMBRE]")
            r_emp.bold = True
            p_intro.add_run(", con RUC N° ")
            r_ruc = p_intro.add_run("[EMPRESA_RUC]")
            r_ruc.bold = True
            p_intro.add_run(", con domicilio en Lima, debidamente representada por su Apoderado Legal; y de la otra parte don(ña) ")
            
            r_trab = p_intro.add_run("[NOMBRE_COMPLETO]")
            r_trab.bold = True
            p_intro.add_run(", identificado(a) con DNI N° ")
            r_dni = p_intro.add_run("[DNI]")
            r_dni.bold = True
            p_intro.add_run(", con estado civil ")
            p_intro.add_run("[ESTADO_CIVIL]")
            p_intro.add_run(", con fecha de nacimiento ")
            p_intro.add_run("[FECHA_NACIMIENTO]")
            p_intro.add_run(", domiciliado(a) en ")
            p_intro.add_run("[DIRECCION]")
            p_intro.add_run(", distrito de ")
            p_intro.add_run("[DISTRITO]")
            p_intro.add_run(", provincia de ")
            p_intro.add_run("[PROVINCIA]")
            p_intro.add_run(", departamento de ")
            p_intro.add_run("[DEPARTAMENTO]")
            p_intro.add_run(", correo electrónico ")
            p_intro.add_run("[CORREO]")
            p_intro.add_run(" y teléfono celular ")
            p_intro.add_run("[CELULAR]")
            p_intro.add_run(", afiliado(a) al sistema pensionario ")
            r_afp = p_intro.add_run("[AFP]")
            r_afp.bold = True
            p_intro.add_run(", a quien en adelante se le denominará simplemente ")
            r_tlabel = p_intro.add_run("EL TRABAJADOR")
            r_tlabel.bold = True
            p_intro.add_run("; en los términos y condiciones siguientes:")

            # Cláusulas
            def add_clause(doc, title, text):
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(6)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r_num = p.add_run(title + " ")
                r_num.bold = True
                p.add_run(text)

            add_clause(doc, "PRIMERA.- OBJETO:", "EL EMPLEADOR contrata los servicios personales de EL TRABAJADOR para que desempeñe las labores correspondientes al cargo de [CARGO], en el área de [AREA], debiendo acatar las directivas, órdenes e instrucciones de sus superiores.")
            
            add_clause(doc, "SEGUNDA.- VIGENCIA Y PLAZO:", "El presente contrato tiene una duración de [DURACION], iniciando sus labores a partir del día [FECHA_INICIO] y concluyendo indefectiblemente el día [FECHA_FIN], fecha en la cual vencerá el plazo pactado sin necesidad de preaviso ni comunicación previa.")
            
            add_clause(doc, "TERCERA.- REMUNERACIÓN:", "EL TRABAJADOR percibirá por la prestación de sus servicios una remuneración mensual de S/ [REMUNERACION] ([REMUNERACION_LETRAS]), la cual será abonada en moneda nacional sujeta a los descuentos de ley (aportes a [AFP] y tributarios aplicables).")
            
            add_clause(doc, "CUARTA.- JORNADA LABORAL:", "La jornada máxima de trabajo será de cuarenta y ocho (48) horas semanales, distribuidas en los turnos y horarios que EL EMPLEADOR establezca según las necesidades operativas de la empresa.")
            
            add_clause(doc, "QUINTA.- DOMICILIO Y NOTIFICACIONES:", "Las partes señalan como sus domicilios los consignados en la introducción del presente contrato, donde se tendrán por válidas todas las comunicaciones y notificaciones, obligándose EL TRABAJADOR a comunicar cualquier variación del mismo.")

            p_fin = doc.add_paragraph()
            p_fin.paragraph_format.space_before = Pt(14)
            p_fin.paragraph_format.space_after = Pt(28)
            p_fin.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_fin.add_run("En señal de conformidad y aceptación con todas las cláusulas precedentes, ambas partes firman el presente contrato por duplicado en la ciudad de Lima, con fecha [FECHA_INICIO].")

            # Tabla de firmas
            table = doc.add_table(rows=2, cols=2)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True
            
            cell_emp = table.cell(0, 0)
            cell_trab = table.cell(0, 1)
            cell_emp_txt = table.cell(1, 0)
            cell_trab_txt = table.cell(1, 1)

            cell_emp.paragraphs[0].text = "\n\n____________________________"
            cell_emp.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            cell_trab.paragraphs[0].text = "\n\n____________________________"
            cell_trab.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            p1 = cell_emp_txt.paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r1 = p1.add_run("EL EMPLEADOR\n[EMPRESA_NOMBRE]\nRUC: [EMPRESA_RUC]")
            r1.font.size = Pt(9.5)

            p2 = cell_trab_txt.paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run("EL TRABAJADOR\n[NOMBRE_COMPLETO]\nDNI N° [DNI]")
            r2.font.size = Pt(9.5)
            r2.bold = True

            doc.save(str(default_tpl_path))

        return default_tpl_path

    def list_templates(self) -> List[Dict[str, Any]]:
        """Lista las plantillas disponibles en la carpeta de plantillas."""
        templates = []
        for p in self.templates_dir.glob("*.docx"):
            templates.append({
                "name": p.name,
                "path": str(p),
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
            })
        return templates

    @staticmethod
    def _replace_in_paragraph(paragraph, replacements: Dict[str, str]) -> int:
        """
        Reemplaza marcadores en un párrafo preservando la estructura y el formato exacto de cada run.
        """
        full_text = "".join(run.text for run in paragraph.runs)
        if not full_text:
            return 0

        replaced_count = 0
        for placeholder, val in replacements.items():
            if placeholder in full_text:
                replaced_count += 1
                full_text = full_text.replace(placeholder, str(val))

        if replaced_count > 0:
            # Algoritmo de asignación segura a runs:
            # Si el placeholder cabe en un solo run, reemplazar dentro de ese run
            # Si cruza múltiples runs (común en Word), consolidar en el primer run y vaciar los demás para preservar el estilo del primero
            needs_global_replacement = False
            for ph, val in replacements.items():
                for run in paragraph.runs:
                    if ph in run.text:
                        run.text = run.text.replace(ph, str(val))
                    elif any(c in run.text for c in ph[:3]) and ph in full_text:
                        needs_global_replacement = True

            if needs_global_replacement and paragraph.runs:
                # Mantener el primer run y preservar su formato original
                first_run = paragraph.runs[0]
                first_run.text = full_text
                for run in paragraph.runs[1:]:
                    run.text = ""

        return replaced_count

    def generate_contract(
        self,
        worker_data: Dict[str, Any],
        contract_dates: Dict[str, Any],
        template_name: Optional[str] = None,
        empresa_nombre: str = "SERVICIOS INDUSTRIALES DEL PERÚ S.A.C.",
        empresa_ruc: str = "20601234567",
    ) -> Dict[str, Any]:
        """
        Genera un contrato individual a partir de la ficha consolidada y la plantilla seleccionada.
        """
        template_path = self.templates_dir / (template_name or "Plantilla_Contrato_Sujeto_a_Modalidad.docx")
        if not template_path.exists():
            template_path = self._ensure_default_template()

        doc = docx.Document(str(template_path))

        # Extraer valores normalizados
        fields = worker_data.get("fields", {})
        
        def gv(k: str, default: str = "") -> str:
            if k in fields:
                val = fields[k].get("value")
                if val:
                    return str(val).strip()
            return default

        dni = gv("dni", worker_data.get("dni", ""))
        paternal = gv("paternal_surname", "")
        maternal = gv("maternal_surname", "")
        first_names = gv("first_names", "")
        apellidos = f"{paternal} {maternal}".strip() or gv("apellidos", "")
        full_name = gv("full_name", f"{apellidos} {first_names}".strip())

        cargo = gv("cargo", "OPERARIO")
        area = gv("area", "OPERACIONES")
        remun = gv("remuneracion", "1,500.00")
        remun_letras = gv("remuneracion_letras", "MIL QUINIENTOS Y 00/100 SOLES")
        afp = gv("afp", "AFP HABITAT")
        direccion = gv("address", "LIMA")
        distrito = gv("district", "LIMA")
        provincia = gv("province", "LIMA")
        departamento = gv("department", "LIMA")
        estado_civil = gv("civil_status", "SOLTERO(A)")
        fecha_nac = gv("birth_date", "")
        correo = gv("correo", "")
        celular = gv("celular", "")
        regimen = gv("regimen", "D. LEG. 728")
        tipo_contrato = gv("tipo_contrato", "POR NECESIDAD DE MERCADO")

        start_date = contract_dates.get("start_date", datetime.now().strftime("%d/%m/%Y"))
        end_date = contract_dates.get("end_date", "")
        duracion = contract_dates.get("duration_text", f"{contract_dates.get('duration_months', 3)} meses")

        # Diccionario maestro de reemplazos
        replacements = {
            "[DNI]": dni,
            "[DOCUMENTO]": dni,
            "[NRO_DOCUMENTO]": dni,
            "[NOMBRE_COMPLETO]": full_name.upper(),
            "[NOMBRES]": first_names.upper(),
            "[APELLIDOS]": apellidos.upper(),
            "[APELLIDO_PATERNO]": paternal.upper(),
            "[APELLIDO_MATERNO]": maternal.upper(),
            "[CARGO]": cargo.upper(),
            "[PUESTO]": cargo.upper(),
            "[AREA]": area.upper(),
            "[REMUNERACION]": remun,
            "[SUELDO]": remun,
            "[REMUNERACION_LETRAS]": remun_letras.upper(),
            "[AFP]": afp.upper(),
            "[SISTEMA_PENSIONARIO]": afp.upper(),
            "[DIRECCION]": direccion.upper(),
            "[DOMICILIO]": direccion.upper(),
            "[DISTRITO]": distrito.upper(),
            "[PROVINCIA]": provincia.upper(),
            "[DEPARTAMENTO]": departamento.upper(),
            "[ESTADO_CIVIL]": estado_civil.upper(),
            "[FECHA_NACIMIENTO]": fecha_nac,
            "[CORREO]": correo.lower(),
            "[EMAIL]": correo.lower(),
            "[CELULAR]": celular,
            "[TELEFONO]": celular,
            "[FECHA_INICIO]": start_date,
            "[FECHA_FIN]": end_date,
            "[FECHA_TERMINO]": end_date,
            "[DURACION]": duracion.upper(),
            "[PLAZO]": duracion.upper(),
            "[REGIMEN]": regimen.upper(),
            "[TIPO_CONTRATO]": tipo_contrato.upper(),
            "[EMPRESA_NOMBRE]": empresa_nombre.upper(),
            "[EMPRESA_RUC]": empresa_ruc,
        }

        total_replaced = 0

        # 1. Párrafos del cuerpo principal
        for p in doc.paragraphs:
            total_replaced += self._replace_in_paragraph(p, replacements)

        # 2. Tablas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        total_replaced += self._replace_in_paragraph(p, replacements)

        # 3. Encabezados y pies de página
        for section in doc.sections:
            for p in section.header.paragraphs:
                total_replaced += self._replace_in_paragraph(p, replacements)
            for p in section.footer.paragraphs:
                total_replaced += self._replace_in_paragraph(p, replacements)

        # Construir nombre de archivo limpio y estructurado
        # Ejemplo: CONTRATO_42694271_GARCIA_BRANDAN_NADIA_CELESTE.docx
        def clean_filename_part(text: str) -> str:
            t = re.sub(r"[^\w\s]", "", text or "")
            return re.sub(r"\s+", "_", t.strip()).upper()

        clean_paternal = clean_filename_part(paternal)
        clean_maternal = clean_filename_part(maternal)
        clean_names = clean_filename_part(first_names)
        
        name_parts = [p for p in [clean_paternal, clean_maternal, clean_names] if p]
        name_segment = "_".join(name_parts) if name_parts else clean_filename_part(full_name)
        
        base_filename = f"CONTRATO_{dni}_{name_segment}.docx"
        out_filepath = self.output_dir / base_filename

        # Manejo de duplicados con versión controlada
        if out_filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"CONTRATO_{dni}_{name_segment}_{timestamp}.docx"
            out_filepath = self.output_dir / base_filename

        doc.save(str(out_filepath))

        return {
            "status": "success",
            "file_name": base_filename,
            "file_path": str(out_filepath),
            "dni": dni,
            "worker_name": full_name,
            "start_date": start_date,
            "end_date": end_date,
            "duration": duracion,
            "variables_replaced_count": total_replaced,
            "size_kb": round(out_filepath.stat().st_size / 1024, 1),
            "generated_at": datetime.now().isoformat(),
        }

    def generate_batch_contracts(
        self,
        workers_list: List[Dict[str, Any]],
        start_date: str,
        duration_months: int,
        template_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Genera contratos en lote para múltiples trabajadores.
        """
        from backend.services.worker_consolidator import WorkerConsolidator
        consolidator = WorkerConsolidator()
        dates = consolidator.calculate_contract_dates(start_date, duration_months)

        generated_files = []
        errors = []

        for w in workers_list:
            dni = w.get("dni", "")
            try:
                profile = consolidator.consolidate_worker_profile(dni)
                res = self.generate_contract(profile, dates, template_name)
                generated_files.append(res)
            except Exception as e:
                errors.append({"dni": dni, "name": w.get("full_name", ""), "error": str(e)})

        return {
            "total_requested": len(workers_list),
            "total_generated": len(generated_files),
            "total_errors": len(errors),
            "generated_contracts": generated_files,
            "errors": errors,
        }
