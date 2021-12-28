#!/usr/bin/python
import sys, os, re, itertools
#CHA:xpastu00
'''
/***********************************************/
/*			Jakub Pastuszek - xpastu00         */
/*				   VUT FIT					   */
/*	  	     CHA: C Header Analysis    		   */
/*				  Duben 2015				   */
/*				    cha.py					   */
/***********************************************/
'''

### Napoveda

help = '''\
###########################################################
Projekt: CHA: C Header Analysis 
Autor: Jakub Pastuszek - xpastu00
\tVUT FIT - Duben 2015
Prehled:
Skript zobrazuje analyzu hlavickovych souboru jazyka C dle standardu ISO C99
Parametry:
--help\tvypise napovedu. Parametr nelze kombinovat s zadnym dalsim parametrem.

--input=fileordir\tZadany vstupni soubor nebo adresar se zdrojovym kodem v jazyce C. \
Predpokladejte, ze soubory budou v kodovani UTF-8. Je-li zadana cesta k adresari, tak jsou \
postupne analyzovany vsechny soubory s priponou .h v tomto adresari a jeho podadresarich. \
Pokud je zadana primo cesta k souboru (nikoliv k adresari), tak priponu souboru nekontrolujte. \
Pokud nebude tento parametr zadan, tak se analyzuji vsechny hlavickove soubory (opet pouze \
s priponou .h) z aktualniho adresare a vsech jeho podadresaru.

--output=filename\tZadany vystupni soubor ve formatu XML v kodovani UTF-8 (presny \
format viz nize). Pokud tento parametr neni zadan, tak dojde k vypsani vysledku na standardni \
vystup.

--pretty-xml=k\tSkript zformatuje vysledny XML dokument tak, ze (1) kazde nove zanoreni \
bude odsazeno o k mezer oproti predchozimu a (2) XML hlavicka bude od korenoveho elementu \
oddelena znakem noveho radku. Pokud k neni zadano, tak se pouzije hodnota 4. Pokud tento \
parametr nebyl zadan, tak se neodsazuje (ani XML hlavicka od korenoveho elementu).

--no-inline\tSkript preskoci funkce deklarovane se specifikatorem inline.

--max-par=n\tSkript bude brat v uvahu pouze funkce, ktere maji n ci mene parametru (n musi \
byt vzdy zadano). U funkci, ktere maji promenny pocet parametru, pocitejte pouze s fixnimi \
parametry.

--no-duplicates\tPokud se v souboru vyskytne vice funkci se stejnym jmenem (napr. \
deklarace funkce a pozdeji jeji definice), tak se do vysledneho XML souboru ulozi pouze prvni \
z nich (uvazujte pruchod souborem shora dolu). Pokud tento parametr neni zadan, tak se do \
vysledneho XML souboru ulozi vsechny vyskyty funkce se stejnym jmenem.

--remove-whitespace\tPri pouziti tohoto parametru skript v obsahu atributu rettype a \
type (viz nize) nahradi vsechny vyskyty jinych bilych znaku, nez je mezera (tabelator, novy \
radek atd.), mezerou a odstrani z nich vsechny prebytecne mezery. Napr. pro funkci "int * \
func(const char arg)" bude hodnota parametru rettype "int*" a hodnota parametru type \
pro parametr bude "const char".

Priklady:
\tcha.py --input=input_file --pretty-xml --no-duplicates
\tcha.py --input=some_dir --no-inline --remove-whitespace --output=file
'''

### Parametry

args_array = [0] * 7    #pomocne pole pro zjisteni duplikace

parI = "./"
parO = sys.stdout
parPX = ""
parNI = False
parMP = "100"
parND = False
parRW = False

argv = sys.argv[1:]

#trida pro zpracovani vyjimky
class ArgERR(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

try:
    for opt in argv:
        if opt.find("--help") != -1:
            print(help)
            sys.exit(0)

        elif opt.find("--input") != -1:
            args_array[0] += 1
            if opt.find('=') != -1:             #vyzaduje = za input
                parI = opt[opt.find('=')+1:]
                if not parI:                    #vyzaduje soubor/slozku za =
                    raise ArgERR(1)
            else:
                raise ArgERR(1)

        elif opt.find("--output") != -1:
            args_array[1] += 1
            if opt.find('=') != -1:             #vyzaduje = za output
                parO = opt[opt.find('=')+1:]
                if not parO:                    #vyzaduje soubor/slozku za =
                    raise ArgERR(1)
            else:
                raise ArgERR(1)

        elif opt.find("--pretty-xml") != -1:
            args_array[2] += 1
            if opt.find('=') != -1:
                parPX = opt[opt.find('=')+1:]   #zadano s parametrem
                if not parPX:
                    raise ArgERR(1)
            else:
                parPX = 4                       #zadano bez parametru

        elif opt.find("--no-inline") != -1:
            args_array[3] += 1
            parNI = True

        elif opt.find("--max-par") != -1:
            args_array[4] += 1
            if opt.find('=') != -1:             #vyzaduje = za max-par
                parMP = opt[opt.find('=')+1:]   #zadano s parametrem
                if not parMP:                   #vyzaduje hodnotu za =
                    raise ArgERR(1)
            else:
                raise ArgERR(1)

        elif opt.find("--no-duplicates") != -1:
            args_array[5] += 1
            parND = True

        elif opt.find("--remove-whitespace") != -1:
            args_array[6] += 1
            parRW = True

        else:
            raise ArgERR(1)

    #duplikace nektereho z parametru
    for i in args_array:
        if i>1:
            raise ArgERR(1)

except ArgERR as e:     #osetreni vyjimky pri zpracovani argumentu
    print("Chyba zpracovani argumentu", file=sys.stderr)
    sys.exit(e.value)

#KONSTANTY PRO AUTOMAT
INIT = 0
MACRO = 1
STRING = 2
STRING2 = 3
COMMENT = 4
COMMENT_L = 5
COMMENT_B = 6
COMMENT_B_END = 7
COMMENT2 = 8
MAC_COM_B = 9
MAC_COM_B_END = 10

#Params: input - otevreny, zpracovavany vstupni soubor
#Return: out - vstupni soubor bez maker, retezcu a komentaru v podobe stringu
def automata (input):
    "Funkce pro odstraneni maker, retezcu a komentaru ze souboru"
    
    state = INIT
    out = ""

    while True:
        c = input.read(1)       #precte jeden znak

        if not c:   #EOF
            break

        if state == INIT:
            if c == '#':
                state = MACRO
            elif c == '"':
                state = STRING
            elif c == '/':          #komentar nebo lomeno
                state = COMMENT
                out += c
            else:                   #validni znak zapis do stringu
                out += c

        elif state == MACRO:
            if c == '\n' and back_up != '\\':
                state = INIT        #end
            elif c == '/':
                state = COMMENT2    #komentar?
            else:
                pass

        elif state == STRING:
            if c == '\\':           #escape
                state = STRING2
            elif c == '"':          #end
                state = INIT
            else:
                pass
        elif state == STRING2:      #pro odstraneni escape sekvence
            state = STRING

        elif state == COMMENT:
            if c == '/':
                state = COMMENT_L
                out = out[:len(out)-1]  #vymazani posledniho znaku
            elif c == '*':
                state = COMMENT_B
                out = out[:len(out)-1]  #vymazani posledniho znaku
            else:
                state = INIT        #neni to komentar

        elif state == COMMENT_L:     #radkovy komentar
            if c == '\n' and back_up != '\\':
                state = INIT
            else:
                pass

        elif state == COMMENT_B:     #blokovy komentar
            if c == '*':
                state = COMMENT_B_END
            else:
                pass
        elif state == COMMENT_B_END:  #za * nemusi byt / (konec blok. komentare)
            if c == '/':            #konec
                state = INIT
            elif c == '*':          #tedka konec?
                state = COMMENT_B_END
            else:
                state = COMMENT_B

        elif state == COMMENT2:
            if c == '/':            #komentar do konce radku
                state = COMMENT_L
            elif c == '*':
                state = MAC_COM_B   #blokovy komentar v makru
            else:
                state = MACRO       #komentar nerozpoznan, stale makro
        elif state == MAC_COM_B:
            if c == '\n':           #novy radek - konec makra
                state = COMMENT_B
            elif c == '*':
                state = MAC_COM_B_END 
            else:
                state = MACRO       #komentar nerozpoznan, stale makro
        elif state == MAC_COM_B_END:  #za * nemusi byt / (konec blok. komentare)
            if c == '/':            #komentar skoncil na temze radku, pokracuje makro
                state = MACRO       
            elif c == '*':          #tedka konec?
                state = MAC_COM_B_END
            elif c == '\n':           #novy radek - konec makra
                state = COMMENT_B
            else:
                state = MAC_COM_B

        back_up=c       #zalohovani predchoziho znaku

    return out      #navrat redukovaneho souboru v podobe stringu

#Params: file - zpracovavany vstupni soubor
#        output - vystupni stream
def parseFile (file, output):
    "Funkce pro pruchod souborem a jeho zpracovani"

    try:
        input = open(file, "r")   #otevreni vstupniho souboru
    except IOError:
        print("Chyba pri otevirani vstupniho souboru ", file, file=sys.stderr)
        sys.exit(2)

    #funkce pro preprocessing
    in_clean = automata(input)

    input.close()   #zavreni vstupniho souboru

    #vzorek pro vyhledani deklarace funkce
    pattern_fun = '''\
        \s*
        (?P<rettype>
          (?:[a-zA-Z_][a-zA-Z0-9_]*[\s\*(]+?)+\s*
        )
        (?P<name>[a-zA-Z_][a-zA-Z0-9_]*)
        (?P<res>\s*)
        
        (?P<params>\(.*?\))
        
        \s*
        (;|{)'''

    p = re.compile(pattern_fun, re.DOTALL | re.VERBOSE)

    array = re.findall(p, in_clean)     #vsechny shody se ulozi do pole

    #string pro seznam vypsanych funkci
    namestr = ''

    for value in array:     #kazda shoda/funkce
        name = value[1]
        rettype = value[0]
        params = value[3]
        res = value[2]
        number = 1
        varargs = 'no'

        if name.strip().lower() == "sizeof":
            continue

        if parNI and rettype.lower().find("inline") != -1:  #vymazani inline funkci
            continue

        #rozdeleni parametru a navratove hodnoty(pretypovani)
        lb = 0
        rb = 0
        num = 0
                
        while True:
            c = params[num]
            num += 1
            if c == '(':
                lb += 1
            elif c == ')':
                rb += 1

            if lb == rb:    #vsechny parametry uzavrene v zavorkach
                break

        rettype += res + params[num:]   #pridani navratove hodnoty(pretypovani) k navratove hodnote
        params = params[1:num-1]        #odebrani navratove hodnoty(pretypovani) z parametru

        #zjisteni zda bylo definovano volitelne mnozstvi parametru
        position = params.find("...")
        if position != -1:
            varargs = 'yes'
            params = params[:position]  #vymazani ...
            position = params.rfind(',')    #pokud to nebyl jediny parametr, vymazani take ,
            if position != -1:
                params = params[:position]

        #rozdeleni parametru
        param = []
        lb = 0
        rb = 0
        num = 0
        
        back = num  #zaloha poradi      
        while True:
            if num >= len(params):
                break
            c = params[num]
            num += 1
            if c == '(':
                lb += 1
            elif c == ')':
                rb += 1
            elif c == ',' and lb == rb:     #dalsi parametr (carka nesmi byt uzavrena v zavorkach)
                param.append(params[back:num-1])   #pridani parametru do listu 
                back = num + 1              #zaloha poradi (zacatek noveho parametru)
                
        param.append(params[back:num])      #pridani posledniho parametru do listu

        #zjisteni poctu parametru
        len_param = len(param)
        if len_param == 1:
            p = param[0].strip(' ') #v zavorce muzou byt mezery/tabelatory nebo void =>
            if not p or p == 'void':    #oprava poctu parametru na 0
                len_param = 0

        #overeni zda pocet parametru funkce neni vetsi nez max-par
        if len_param > int(parMP):
            continue

        #nezapsani duplikatnich funkci
        if parND and namestr.find(name) != -1:
            continue

        #zaznamenani jmena funkce
        namestr += name + ';'

        #vlozeni mezer podle hodnoty pretty-xml pred function
        if parPX:
            output.write('\n')
            for _ in itertools.repeat(None, int(parPX)):
                output.write(' ')

        pattern_ws = '\s+'          #vzorek pro odstraneni prebytecnych mezer
        pattern_star = '\s*\*\s*'   #vzorek pro odstraneni prebytecnych mezer, kde se vyskytuji *
        pattern_iden = '\w+'

        #mazani vice mezer/tabelatoru
        if parRW:
            rettype = re.sub(pattern_ws, ' ', rettype)
            rettype = re.sub(pattern_star, '*', rettype)
   
        #file relativne k dir
        if file.find(parI) != -1:
            file = file[len(parI):]

        output.write('<function file="' + file + '" name="' + name)
        output.write('" varargs="' + varargs + '" rettype="' + rettype.strip() + '">') 

        if params:      #funkce ma parametry
            for p in param:     #parametr za parametrem
                p = p.strip()
                if p != 'void':
                    #vlozeni mezer podle hodnoty pretty-xml pred param
                    if parPX:
                        output.write('\n')
                        for _ in itertools.repeat(None, int(parPX)*2):
                            output.write(' ')

                    #mazani vice mezer/tabelatoru
                    if parRW:
                        p = re.sub(pattern_ws, ' ', p)
                        p = re.sub(pattern_star, '*', p)

                    pos1 = p.rfind(' ')     #nalezeni nejpravejsi mezery
                    pos2 = p.rfind('*')     #nalezeni nejpravejsi dereference
                    pos3 = p.rfind(")")     #nalezeni nejpravejsi uzaviraci zavorky

                    #oriznuti co nejvice vpravo (jen identifikator)
                    pos1 = max(pos1, pos2, pos3)

                    #klicova slova ktera nesmi byt nahrazena-neresi typedef
                    list_types = "int,long,short,double,char,float,const".split(',')
 
                    z = re.compile(pattern_iden)    #vybrani nepravejsiho klic. slova/identifikatoru

                    zarray = re.findall(z, p[pos1+1:])     #vsechny shody se ulozi do pole
                    
                    #vybrane slovo neni klic. slovo a neni to jedine slovo argumentu
                    if not any(x in list_types for x in zarray) and p.strip().find(' ') != -1:
                        p = p[:pos1+1] + re.sub(pattern_iden, '', p[pos1+1:])

                    output.write('<param number="' + str(number) + '" type="' + p.strip() + '" />') 
                    number += 1

        #vlozeni mezer podle hodnoty pretty-xml pred konec function
        if parPX:
            output.write('\n')
            for _ in itertools.repeat(None, int(parPX)):
                output.write(' ')

        output.write('</function>') 

    return

#OTEVRENI VYSTUPNIHO SOUBORU
if parO != sys.stdout:
    try:
        output = open(parO, "w")    #otevreni vystupniho souboru
    except IOError:
        print("Chyba pri otevirani vystupniho souboru ", parO, file=sys.stderr)
        sys.exit(3)
else:
    output = parO       #vypis na STDOUT    

#Overeni zda byl za parametrem input zadan validni soubor/slozka
if os.path.isdir(os.path.join(os.path.abspath('.'), parI)):
    pass
elif os.path.isfile(os.path.join(os.path.abspath('.'), parI)):
    pass
else:
    print("Chyba pri otevirani vstupniho souboru ", parI, file=sys.stderr)
    sys.exit(2)

#XML hlavicka
output.write('<?xml version="1.0" encoding="utf-8"?>')

if parPX:
    output.write('\n')

#Zjisteni zda zadany input je soubor
if os.path.isfile(os.path.join(os.path.abspath('.'), parI)):
    file = parI
    parI = ""
    output.write('<functions dir="">')
    parseFile(file, output)
else:
    output.write('<functions dir="' + parI + '">')
    #Pruchod slozkou a podslozkami
    for root, dirs, files in os.walk(parI):
        for name in files:
            file = os.path.join(root, name)
            if file[-2:] == '.h':           #prohledavaji se jen .h soubory
                parseFile(file, output)

if parPX:
    output.write('\n')
output.write('</functions>\n')

if parO != sys.stdout:  #uzavreni vystupniho souboru, pokud se nevypisovalo na STDOUT
    output.close()