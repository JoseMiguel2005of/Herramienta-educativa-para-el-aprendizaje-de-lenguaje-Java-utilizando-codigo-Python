// glossary-tooltips.js - Sistema global de glosario y tooltips educativos

const GLOSSARY_MASTER = [
    // --- FUNDAMENTOS Y TIPOS ---
    {
        term: 'Variable',
        alt: 'variable',
        def: 'Espacio en memoria identificado con un nombre que almacena un valor susceptible de cambiar durante la ejecución.',
        tooltip: 'Contenedor en memoria para guardar datos que pueden cambiar.',
        tags: ['básico', 'python', 'java']
    },
    {
        term: 'Constante',
        alt: 'constant / final',
        def: 'Valor que no cambia durante la ejecución del programa. En Java se usa final; en Python se indica por convención con MAYÚSCULAS.',
        tooltip: 'Valor fijo en memoria que no cambia una vez definido.',
        tags: ['básico', 'python', 'java']
    },
    {
        term: 'Tipo de dato',
        alt: 'data type',
        def: 'Clasificación que indica al compilador o intérprete qué tipo de valor almacena una variable (número, texto, etc.).',
        tooltip: 'Clasificación de un valor (números, texto, booleanos, etc.).',
        tags: ['básico', 'tipos']
    },
    {
        term: 'Int',
        alt: 'int / Integer',
        def: 'Tipo de dato para números enteros sin decimales. Python maneja precisión arbitraria; Java tiene int de 32 bits.',
        tooltip: 'Número entero (positivo, negativo o cero, sin decimales).',
        tags: ['tipos', 'python', 'java']
    },
    {
        term: 'Float',
        alt: 'float / double',
        def: 'Tipo de dato para números con punto decimal o punto flotante.',
        tooltip: 'Número con decimales (ejemplo: 3.14 o -0.5).',
        tags: ['tipos', 'python', 'java']
    },
    {
        term: 'String',
        alt: 'str / String',
        def: 'Secuencia ordenada de caracteres de texto. En ambos lenguajes es inmutable.',
        tooltip: 'Cadena de texto delimitada por comillas.',
        tags: ['tipos', 'python', 'java']
    },
    {
        term: 'Booleano',
        alt: 'bool / boolean',
        def: 'Tipo de dato lógico que solo puede tener dos estados: True/False (Python) o true/false (Java).',
        tooltip: 'Valor lógico que representa Verdadero (True) o Falso (False).',
        tags: ['tipos', 'python', 'java']
    },
    {
        term: 'Casting',
        alt: 'type casting / conversión',
        def: 'Proceso de convertir un valor de un tipo de dato a otro (ej: convertir texto a entero).',
        tooltip: 'Conversión explícita de un tipo de dato a otro (ej: str a int).',
        tags: ['tipos', 'python', 'java']
    },
    {
        term: 'Mutable',
        alt: 'mutability',
        def: 'Propiedad de los objetos cuyo estado o contenido puede modificarse después de ser creados (ej: listas, diccionarios).',
        tooltip: 'Objeto cuyo contenido se puede modificar después de crearse.',
        tags: ['conceptos', 'python']
    },
    {
        term: 'Inmutable',
        alt: 'immutability',
        def: 'Objeto cuyo valor no puede ser alterado tras su creación (ej: strings, tuplas, números).',
        tooltip: 'Objeto que no puede modificarse tras crearse; para cambiarlo se crea uno nuevo.',
        tags: ['conceptos', 'python', 'java']
    },
    {
        term: 'Indentación',
        alt: 'indentation',
        def: 'Espaciado al inicio de una línea de código. En Python define la jerarquía y bloques lógicos en lugar de llaves {}.',
        tooltip: 'Espacios al inicio de línea que definen los bloques de código en Python.',
        tags: ['sintaxis', 'python']
    },
    {
        term: 'Scope',
        alt: 'ámbito / alcance',
        def: 'Región del código donde una variable o función es accesible y existe (local, global, etc.).',
        tooltip: 'Ámbito o zona del programa donde una variable es visible y utilizable.',
        tags: ['conceptos', 'python', 'java']
    },

    // --- ESTRUCTURAS DE DATOS ---
    {
        term: 'Lista',
        alt: 'list / ArrayList',
        def: 'Colección ordenada y mutable de elementos. En Python es list; en Java se usa ArrayList.',
        tooltip: 'Colección ordenada de elementos que se puede modificar, agregar o eliminar.',
        tags: ['colecciones', 'python', 'java']
    },
    {
        term: 'Tupla',
        alt: 'tuple',
        def: 'Colección ordenada e inmutable de elementos, delimitada por paréntesis (). Exclusiva de Python.',
        tooltip: 'Colección ordenada e inmutable de datos (no se puede modificar tras crearse).',
        tags: ['colecciones', 'python']
    },
    {
        term: 'Diccionario',
        alt: 'dict / HashMap',
        def: 'Estructura asociativa que almacena datos en pares clave-valor. Python: dict, Java: HashMap.',
        tooltip: 'Colección de elementos indexados por claves únicas (clave: valor).',
        tags: ['colecciones', 'python', 'java']
    },
    {
        term: 'Set',
        alt: 'set / HashSet',
        def: 'Colección no ordenada de elementos únicos sin duplicados.',
        tooltip: 'Conjunto de elementos únicos sin orden garantizado ni duplicados.',
        tags: ['colecciones', 'python', 'java']
    },
    {
        term: 'Array',
        alt: 'arreglo / vector',
        def: 'Estructura contigua de tamaño fijo que almacena elementos del mismo tipo de dato.',
        tooltip: 'Arreglo de elementos contiguos en memoria del mismo tipo.',
        tags: ['colecciones', 'java', 'numpy']
    },
    {
        term: 'DataFrame',
        alt: 'pandas.DataFrame',
        def: 'Estructura bidimensional de datos tabulares (filas y columnas) provista por la biblioteca Pandas.',
        tooltip: 'Tabla bidimensional con filas y columnas etiquetadas en Pandas.',
        tags: ['data science', 'pandas']
    },
    {
        term: 'Series',
        alt: 'pandas.Series',
        def: 'Arreglo unidimensional etiquetado capaz de almacenar cualquier tipo de datos en Pandas.',
        tooltip: 'Columna unidimensional de datos con etiquetas/índices en Pandas.',
        tags: ['data science', 'pandas']
    },
    {
        term: 'Matriz',
        alt: 'matrix / 2D array',
        def: 'Estructura de datos bidimensional organizada en filas y columnas.',
        tooltip: 'Estructura de datos en tabla compuesta por filas y columnas.',
        tags: ['colecciones', 'numpy']
    },
    {
        term: 'Slicing',
        alt: 'rebanado [inicio:fin]',
        def: 'Técnica en Python para extraer una porción o subsecuencia de una lista, tupla o string con [inicio:fin:paso].',
        tooltip: 'Técnica de Python para extraer un rango o porción de una secuencia ([a:b]).',
        tags: ['sintaxis', 'python']
    },

    // --- PROGRAMACIÓN ORIENTADA A OBJETOS (POO) ---
    {
        term: 'Clase',
        alt: 'class',
        def: 'Plantilla o molde a partir del cual se crean objetos, definiendo sus atributos y métodos.',
        tooltip: 'Molde o plantilla para crear objetos con propiedades y comportamientos.',
        tags: ['OOP', 'python', 'java']
    },
    {
        term: 'Objeto',
        alt: 'object / instancia',
        def: 'Entidad individual creada a partir de una clase, que posee estado (atributos) y comportamiento (métodos).',
        tooltip: 'Instancia concreta de una clase con datos y funciones propias.',
        tags: ['OOP', 'python', 'java']
    },
    {
        term: 'Método',
        alt: 'method',
        def: 'Función asociada a una clase o a un objeto que describe su comportamiento o modifica su estado.',
        tooltip: 'Función definida dentro de una clase que actúa sobre sus objetos.',
        tags: ['OOP', 'python', 'java']
    },
    {
        term: 'Constructor',
        alt: '__init__ / Constructor',
        def: 'Método especial que se ejecuta automáticamente al instanciar un objeto para inicializar sus atributos.',
        tooltip: 'Método que inicializa los valores de un objeto al crearlo (__init__ en Python).',
        tags: ['OOP', 'python', 'java']
    },
    {
        term: 'Herencia',
        alt: 'inheritance',
        def: 'Mecanismo mediante el cual una clase hija adquiere atributos y métodos de una clase padre.',
        tooltip: 'Capacidad de una clase para heredar características y métodos de otra.',
        tags: ['OOP', 'python', 'java']
    },
    {
        term: 'Polimorfismo',
        alt: 'polymorphism',
        def: 'Capacidad de diferentes clases para responder al mismo mensaje o método con comportamientos específicos.',
        tooltip: 'Capacidad de distintos objetos de responder de forma única a un mismo método.',
        tags: ['OOP', 'avanzado']
    },
    {
        term: 'Encapsulamiento',
        alt: 'encapsulation',
        def: 'Ocultamiento del estado interno y detalles de implementación de un objeto, exponiendo solo interfaces seguras.',
        tooltip: 'Ocultar los datos internos de un objeto para protegerlos de accesos indebidos.',
        tags: ['OOP', 'avanzado']
    },
    {
        term: 'Abstracción',
        alt: 'abstraction',
        def: 'Principio de simplificar la complejidad enfocándose en los aspectos esenciales de un objeto e ignorando detalles irrelevantes.',
        tooltip: 'Enfocarse en lo esencial de un concepto ocultando la complejidad interna.',
        tags: ['OOP', 'conceptos']
    },
    {
        term: 'Interface',
        alt: 'interface / interfaz',
        def: 'Contrato que define qué métodos debe implementar una clase, sin incluir su código.',
        tooltip: 'Contrato de métodos que una clase debe cumplir e implementar obligatoriamente.',
        tags: ['OOP', 'java']
    },
    {
        term: 'Static',
        alt: 'static / @staticmethod',
        def: 'Miembro o método que pertenece a la clase en general y no a instancias individuales de la misma.',
        tooltip: 'Atributo o método que pertenece a la clase misma y no a sus objetos creados.',
        tags: ['OOP', 'python', 'java']
    },

    // --- FUNCIONES Y CONTROL DE FLUJO ---
    {
        term: 'Función',
        alt: 'function / def',
        def: 'Bloque de código modular y reutilizable que realiza una tarea específica y puede retornar un resultado.',
        tooltip: 'Bloque de código reutilizable que recibe entradas y produce un resultado.',
        tags: ['básico', 'python', 'java']
    },
    {
        term: 'Parámetro',
        alt: 'parameter',
        def: 'Variable declarada en la definición de una función para recibir datos al ser invocada.',
        tooltip: 'Variable que espera una función al momento de ser definida.',
        tags: ['básico', 'python', 'java']
    },
    {
        term: 'Argumento',
        alt: 'argument',
        def: 'Valor real que se le envía a una función al momento de llamarla o ejecutarla.',
        tooltip: 'Valor real que le pasas a una función al ejecutarla.',
        tags: ['básico', 'python', 'java']
    },
    {
        term: 'Bucle',
        alt: 'loop / ciclo',
        def: 'Estructura de control que repite un bloque de código mientras se cumpla una condición o sobre una secuencia.',
        tooltip: 'Estructura que repite instrucciones (for o while).',
        tags: ['control', 'básico']
    },
    {
        term: 'Condicional',
        alt: 'if / else / switch',
        def: 'Estructura que toma decisiones ejecutando diferentes bloques de código según una condición booleana.',
        tooltip: 'Instrucción que ejecuta un bloque de código si una condición es verdadera (if/else).',
        tags: ['control', 'básico']
    },
    {
        term: 'Lambda',
        alt: 'función anónima / arrow',
        def: 'Función pequeña y anónima definida en una sola línea de código sin nombre formal.',
        tooltip: 'Función anónima y compacta de una sola línea (lambda x: x*2).',
        tags: ['avanzado', 'python', 'java']
    },
    {
        term: 'Recursión',
        alt: 'recursion / recursividad',
        def: 'Técnica de programación donde una función se llama a sí misma para resolver un problema dividiéndolo en casos base.',
        tooltip: 'Función que se llama a sí misma para resolver un problema por partes.',
        tags: ['avanzado', 'algoritmos']
    },
    {
        term: 'Callback',
        alt: 'función de retorno',
        def: 'Función que se pasa como argumento a otra función para ser ejecutada después de que ocurra un evento.',
        tooltip: 'Función que se pasa como parámetro para ejecutarse al terminar una tarea.',
        tags: ['avanzado', 'conceptos']
    },
    {
        term: 'Generador',
        alt: 'generator / yield',
        def: 'Función especial en Python que produce una secuencia de valores bajo demanda usando yield en lugar de return.',
        tooltip: 'Función que genera valores uno a uno bajo demanda con yield, ahorrando memoria.',
        tags: ['avanzado', 'python']
    },
    {
        term: 'Iterador',
        alt: 'iterator',
        def: 'Objeto que permite recorrer los elementos de una colección uno a la vez mediante el método __next__().',
        tooltip: 'Objeto que permite recorrer una secuencia de elementos paso a paso.',
        tags: ['avanzado', 'python', 'java']
    },

    // --- ARQUITECTURA, COMPILACIÓN Y ERRORES ---
    {
        term: 'Compilador',
        alt: 'compiler (javac)',
        def: 'Programa que traduce código fuente humano a código binario o bytecode antes de su ejecución.',
        tooltip: 'Traduce todo el código fuente a código máquina antes de ejecutarlo.',
        tags: ['arquitectura', 'java']
    },
    {
        term: 'Intérprete',
        alt: 'interpreter (python)',
        def: 'Programa que lee y ejecuta el código fuente instrucción por instrucción en tiempo real.',
        tooltip: 'Ejecuta el código fuente línea por línea en tiempo real (como Python).',
        tags: ['arquitectura', 'python']
    },
    {
        term: 'Transpilador',
        alt: 'transpiler / source-to-source',
        def: 'Herramienta que traduce el código fuente de un lenguaje de programación a otro lenguaje de nivel similar (ej: Python a Java).',
        tooltip: 'Traductor de código que convierte un lenguaje a otro (ej: Python a Java).',
        tags: ['arquitectura', 'transpiler']
    },
    {
        term: 'Bytecode',
        alt: 'código intermedio (.class / .pyc)',
        def: 'Forma intermedia de código generada por el compilador para ser ejecutada por una máquina virtual (JVM o PVM).',
        tooltip: 'Código intermedio optimizado para ejecutarse en una máquina virtual.',
        tags: ['arquitectura', 'java', 'python']
    },
    {
        term: 'JVM',
        alt: 'Java Virtual Machine',
        def: 'Máquina Virtual de Java encargada de ejecutar el bytecode de Java en cualquier sistema operativo.',
        tooltip: 'Máquina Virtual de Java que permite ejecutar código Java en cualquier computadora.',
        tags: ['arquitectura', 'java']
    },
    {
        term: 'Excepción',
        alt: 'exception / error',
        def: 'Evento anómalo que interrumpe el flujo normal del programa durante su ejecución.',
        tooltip: 'Error que ocurre durante la ejecución del programa y que puede ser capturado.',
        tags: ['errores', 'python', 'java']
    },
    {
        term: 'Debugging',
        alt: 'depuración',
        def: 'Proceso de identificar, aislar y corregir errores o fallos en el código fuente de un software.',
        tooltip: 'Proceso de buscar y solucionar fallos o errores en el código.',
        tags: ['buenas prácticas']
    },
    {
        term: 'API',
        alt: 'Application Programming Interface',
        def: 'Conjunto de reglas y protocolos que permite que diferentes aplicaciones de software se comuniquen entre sí.',
        tooltip: 'Interfaz que permite a dos programas comunicarse e intercambiar datos.',
        tags: ['web', 'arquitectura']
    },
    {
        term: 'JSON',
        alt: 'JavaScript Object Notation',
        def: 'Formato ligero de intercambio de datos basado en texto legible para humanos y máquinas.',
        tooltip: 'Formato estándar y ligero de texto para intercambiar datos estructurados.',
        tags: ['web', 'datos']
    },
    {
        term: 'REST',
        alt: 'Representational State Transfer',
        def: 'Estilo de arquitectura de software para sistemas hipermedia distribuidos, comúnmente usado en APIs web con HTTP.',
        tooltip: 'Estándar de diseño para construir servicios web y APIs mediante HTTP.',
        tags: ['web', 'arquitectura']
    },

    // --- BASES DE DATOS Y DATA SCIENCE ---
    {
        term: 'SQL',
        alt: 'Structured Query Language',
        def: 'Lenguaje estándar para almacenar, manipular y recuperar datos estructurados en bases de datos relacionales.',
        tooltip: 'Lenguaje estándar para consultar y manipular bases de datos relacionales.',
        tags: ['bases de datos', 'sql']
    },
    {
        term: 'MongoDB',
        alt: 'NoSQL Database',
        def: 'Base de datos NoSQL orientada a documentos que almacena datos en formato flexible similar a JSON (BSON).',
        tooltip: 'Base de datos NoSQL que guarda datos en documentos flexibles tipo JSON.',
        tags: ['bases de datos', 'nosql']
    },
    {
        term: 'CRUD',
        alt: 'Create, Read, Update, Delete',
        def: 'Acrónimo de las cuatro operaciones básicas sobre datos: Crear, Leer, Actualizar y Eliminar.',
        tooltip: 'Las 4 operaciones esenciales de una base de datos: Crear, Leer, Actualizar y Borrar.',
        tags: ['bases de datos', 'conceptos']
    },
    {
        term: 'Clave Primaria',
        alt: 'Primary Key / PK',
        def: 'Columna o conjunto de columnas que identifica de forma única e inequívoca cada registro de una tabla relacional.',
        tooltip: 'Identificador único e irrepetible para cada fila de una tabla en la base de datos.',
        tags: ['bases de datos', 'sql']
    },
    {
        term: 'Clave Foránea',
        alt: 'Foreign Key / FK',
        def: 'Columna que establece una relación vincular con la clave primaria de otra tabla.',
        tooltip: 'Columna que vincula una tabla con la clave de otra tabla relacional.',
        tags: ['bases de datos', 'sql']
    },
    {
        term: 'NumPy',
        alt: 'Numerical Python',
        def: 'Biblioteca fundamental de Python para el cálculo numérico y operaciones eficientes con matrices y arreglos.',
        tooltip: 'Librería de Python para cálculo numérico rápido y operaciones matemáticas con matrices.',
        tags: ['data science', 'numpy']
    },
    {
        term: 'Pandas',
        alt: 'Python Data Analysis',
        def: 'Biblioteca de Python diseñada para la manipulación y análisis estructurado de datos mediante DataFrames.',
        tooltip: 'Librería de Python para análisis, limpieza y manipulación de datos tabulares.',
        tags: ['data science', 'pandas']
    },
    {
        term: 'SciPy',
        alt: 'Scientific Python',
        def: 'Biblioteca de Python para computación científica avanzada, optimización, estadística y álgebra lineal.',
        tooltip: 'Librería para cálculo científico, algoritmos matemáticos y estadísticas avanzadas.',
        tags: ['data science', 'scipy']
    },
    {
        term: 'Query',
        alt: 'consulta',
        def: 'Instrucción o solicitud enviada a una base de datos para extraer, filtrar o modificar información.',
        tooltip: 'Instrucción o petición enviada a la base de datos para obtener o modificar información.',
        tags: ['bases de datos', 'sql']
    }
];

if (typeof window !== 'undefined') {
    window.GLOSSARY_MASTER = GLOSSARY_MASTER;
}

// Palabras demasiado ambiguas en prosa en español/inglés para auto-resaltar vía alias "alt"
const EXCLUDED_ALT_TERMS = new Set([
    'final',
    'error',
    'else',
    'for',
    'if',
    'arrow',
    'consulta'
]);

let _cachedGlossaryMatcher = null;

function buildGlossaryMatcher() {
    if (_cachedGlossaryMatcher) return _cachedGlossaryMatcher;

    const termMap = new Map();
    GLOSSARY_MASTER.forEach(item => {
        const tooltip = item.tooltip || item.def;
        const primary = item.term.trim().toLowerCase();
        if (primary) {
            termMap.set(primary, tooltip);
        }
        if (item.alt) {
            const parts = item.alt
                .split(/[\/,]/)
                .map(p => p.trim())
                .filter(p => p.length > 2 && !/[()\[\]]/.test(p));
            parts.forEach(p => {
                const key = p.toLowerCase();
                if (!EXCLUDED_ALT_TERMS.has(key) && !termMap.has(key)) {
                    termMap.set(key, tooltip);
                }
            });
        }
    });

    // Ordenar términos por longitud descendente para evitar colisiones parciales
    const sortedTerms = Array.from(termMap.keys()).sort((a, b) => b.length - a.length);
    const pattern = sortedTerms
        .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
        .join('|');

    // Compilar la expresión regular UNA SOLA VEZ con límites Unicode (\p{L}, \p{N}, _) para soportar tildes
    let regex;
    try {
        regex = new RegExp(`(?<![\\p{L}\\p{N}_])(${pattern})(?![\\p{L}\\p{N}_])`, 'giu');
    } catch (e) {
        regex = new RegExp(`\\b(${pattern})\\b`, 'gi');
    }

    _cachedGlossaryMatcher = { termMap, regex };
    return _cachedGlossaryMatcher;
}

// Función para inicializar los tooltips en la página actual
function initGlossaryTooltips() {
    const targetSelectors = [
        '.section-text',
        '.note-body',
        '.lesson-body',
        '.theory-card',
        '.exercise-description',
        '.practice-desc',
        '.reference-desc',
        '.concept-text',
        '.overview-text'
    ];

    const elements = document.querySelectorAll(targetSelectors.join(', '));
    if (!elements || elements.length === 0) return;

    const { termMap, regex } = buildGlossaryMatcher();

    elements.forEach(container => {
        const walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function (node) {
                    const parent = node.parentElement;
                    if (!parent) return NodeFilter.FILTER_REJECT;
                    const tag = parent.tagName.toLowerCase();
                    if (['code', 'pre', 'script', 'style', 'a', 'button', 'input', 'textarea', 'select', 'span', 'abbr'].includes(tag)) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    if (parent.classList.contains('glossary-term')) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );

        const nodesToReplace = [];
        let currentNode;
        while ((currentNode = walker.nextNode())) {
            if (currentNode.nodeValue && currentNode.nodeValue.trim().length > 0) {
                nodesToReplace.push(currentNode);
            }
        }

        nodesToReplace.forEach(textNode => {
            const text = textNode.nodeValue;
            regex.lastIndex = 0;

            let match;
            let lastIndex = 0;
            let fragment = null;

            while ((match = regex.exec(text)) !== null) {
                const matchedWord = match[0];
                const def = termMap.get(matchedWord.toLowerCase());
                if (!def) continue;

                if (!fragment) {
                    fragment = document.createDocumentFragment();
                }

                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                }

                // Sin tabindex="0" para evitar inyectar decenas de paradas de tabulación en párrafos
                const termSpan = document.createElement('span');
                termSpan.className = 'glossary-term';
                termSpan.setAttribute('data-tooltip', def);
                termSpan.setAttribute('title', def);
                termSpan.textContent = matchedWord;
                fragment.appendChild(termSpan);

                lastIndex = match.index + matchedWord.length;
            }

            if (fragment) {
                if (lastIndex < text.length) {
                    fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
                }
                if (textNode.parentNode) {
                    textNode.parentNode.replaceChild(fragment, textNode);
                }
            }
        });
    });

    // Soporte táctil ligero sin contaminar el orden de tabulación
    document.addEventListener('click', (e) => {
        const term = e.target.closest('.glossary-term');
        document.querySelectorAll('.glossary-term.tooltip-open').forEach(el => {
            if (el !== term) el.classList.remove('tooltip-open');
        });
        if (term) {
            term.classList.toggle('tooltip-open');
        }
    });
}

if (typeof window !== 'undefined') {
    window.buildGlossaryMatcher = buildGlossaryMatcher;
}

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGlossaryTooltips);
    } else {
        initGlossaryTooltips();
    }
}
