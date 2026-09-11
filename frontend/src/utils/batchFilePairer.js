/**
 * batchFilePairer.js
 * 
 * Agrupa y empareja archivos de imágenes de DNI subidos en lote según sus nombres:
 * - Patrones Anverso (A): DNI-A, DNI_A, 1.A, 1_A, 1-A, 1A, DNI_XXXX_A, TRABAJADOR_01_ANVERSO, FRONT, etc.
 * - Patrones Reverso (R): DNI-R, DNI_R, 1.R, 1_R, 1-R, 1R, DNI_XXXX_R, TRABAJADOR_01_REVERSO, BACK, etc.
 * - Imágenes individuales (sin sufijo de cara): tratadas como Anverso único.
 */

export function parseSideAndIdentifier(fileName) {
  // Quitar extensión
  const lastDotIdx = fileName.lastIndexOf('.');
  const baseName = lastDotIdx !== -1 ? fileName.substring(0, lastDotIdx) : fileName;
  const ext = lastDotIdx !== -1 ? fileName.substring(lastDotIdx + 1) : '';

  // 1. Patrón: Separador + A / ANVERSO / FRONT al final
  // Ejemplos: "1.A", "1_A", "1-A", "1 A", "DNI_44889922_A", "DNI-A", "doc_anverso", "juan_front"
  const frontRegex = /^(.*?)[._\-\s]*(?:A|ANVERSO|FRONT|CARA1|CARA_A|FRENTE)$/i;
  // 2. Patrón: Separador + R / REVERSO / BACK al final
  // Ejemplos: "1.R", "1_R", "1-R", "1 R", "DNI_44889922_R", "DNI-R", "doc_reverso", "juan_back"
  const backRegex = /^(.*?)[._\-\s]*(?:R|REVERSO|BACK|CARA2|CARA_R|POSTERIOR|ATRAS)$/i;

  // 3. Patrón directo sin separador pero con dígitos precedentes: e.g. "1A", "02A", "10R"
  const directFrontRegex = /^(.*?\d+)A$/i;
  const directBackRegex = /^(.*?\d+)R$/i;

  // Verificar Reverso primero
  let backMatch = baseName.match(backRegex) || baseName.match(directBackRegex);
  if (backMatch) {
    const rawId = backMatch[1].trim() || 'DNI';
    return {
      identifier: normalizeIdentifier(rawId),
      displayId: rawId,
      side: 'back',
      originalName: fileName,
      ext
    };
  }

  // Verificar Anverso
  let frontMatch = baseName.match(frontRegex) || baseName.match(directFrontRegex);
  if (frontMatch) {
    const rawId = frontMatch[1].trim() || 'DNI';
    return {
      identifier: normalizeIdentifier(rawId),
      displayId: rawId,
      side: 'front',
      originalName: fileName,
      ext
    };
  }

  // Si no tiene sufijo de cara conocido, se asume que es un DNI individual (anverso o tarjeta única)
  return {
    identifier: normalizeIdentifier(baseName),
    displayId: baseName,
    side: 'front',
    isSingle: true,
    originalName: fileName,
    ext
  };
}

function normalizeIdentifier(str) {
  // Elimina caracteres especiales redundantes al final/inicio para agrupar limpiamente
  return str.trim().toLowerCase().replace(/^[._\-\s]+|[._\-\s]+$/g, '');
}

/**
 * Agrupa una lista de archivos File en pares estructurados.
 * @param {File[]} files - Lista de archivos subidos
 * @returns {Array} Lista de pares ordenados { id, label, frontFile, backFile, status, ... }
 */
export function pairBatchFiles(files) {
  if (!files || files.length === 0) return [];

  const groups = new Map();

  Array.from(files).forEach((file, index) => {
    const parsed = parseSideAndIdentifier(file.name);
    const key = parsed.identifier || `item_${index}`;

    if (!groups.has(key)) {
      groups.set(key, {
        id: `pair_${key}_${Date.now()}_${index}`,
        key: key,
        label: parsed.displayId || `Documento ${groups.size + 1}`,
        frontFile: null,
        backFile: null,
        frontName: null,
        backName: null,
        status: 'pending', // 'pending' | 'processing' | 'done' | 'error'
        extractedData: null,
        savedRecord: null,
        error: null,
        createdAt: new Date().toISOString()
      });
    }

    const group = groups.get(key);

    if (parsed.side === 'front') {
      // Si ya existía un front y este es nuevo, asignarlo o si era single
      group.frontFile = file;
      group.frontName = file.name;
    } else if (parsed.side === 'back') {
      group.backFile = file;
      group.backName = file.name;
    }
  });

  // Convertir mapa a array y ordenar numéricamente/alfabéticamente por etiqueta
  const result = Array.from(groups.values()).sort((a, b) => {
    // Intentar ordenación numérica natural (e.g. 1, 2, 3, 10...)
    const numA = parseInt(a.label, 10);
    const numB = parseInt(b.label, 10);
    if (!isNaN(numA) && !isNaN(numB)) {
      return numA - numB;
    }
    return a.label.localeCompare(b.label, undefined, { numeric: true, sensitivity: 'base' });
  });

  return result;
}
