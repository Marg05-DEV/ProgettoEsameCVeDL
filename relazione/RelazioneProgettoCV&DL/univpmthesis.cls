%%
%% This is file `univpmthesis.cls',
%% generated with the docstrip utility.
%%
%% The original source files were:
%%
%% univpmthesis.dtx  (with options: `class')
%% _______________________________________________________________
%% 
%% The univpmthesis class for typesetting the thesis
%% work of Università Politecnica delle Marche.
%%
%% The template is based on univpmphdthesis class, developed by
%% Marco Giammarini
%% 
%% Copyright (C) UNIVPM 2018-2020
%% 
%% This work may be distributed and/or modified under the
%% conditions of the LaTeX Project Public License, either
%% version 1.3 of this license or (at your option) any later
%% version. The latest version of this license is in
%% 
%%   http://www.latex-project.org/lppl.txt
%% 
%% and version 1.3 or later is part of all distributions of LaTeX
%% version 2005/12/01 or later.
%% 
%% _______________________________________________________________
%% 
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{univpmthesis}%
  [2020/10/02 v.1.0 Template for thesis of Universita' Politecnica delle Marche]
\errorcontextlines=9
%% Carico ifthen e dichiaro i booleani per le opzioni
\RequirePackage{ifthen,etoolbox}

\newif\ifunivpm@aquattroprint \univpm@aquattroprintfalse
\newif\ifunivpm@english       \univpm@englishfalse
\newif\ifunivpm@italian       \univpm@italianfalse
\newif\ifunivpm@lof           \univpm@loffalse
\newif\ifunivpm@lot           \univpm@lotfalse
\newif\ifunivpm@oneside       \univpm@onesidefalse
\newif\ifunivpm@twoside       \univpm@twosidefalse

%% Dichiaro le opzioni
\DeclareOption{a4print}{\univpm@aquattroprinttrue}
\DeclareOption{english}{\univpm@englishtrue}
\DeclareOption{italian}{\univpm@italiantrue}
\DeclareOption{lof}{\univpm@loftrue}
\DeclareOption{lot}{\univpm@lottrue}
\DeclareOption{oneside}{\univpm@onesidetrue}
\DeclareOption{twoside}{\univpm@twosidetrue}

\DeclareOption*{
  \ClassError{univpmthesis}%
    {L'opzione \CurrentOption\space non e' valida}%
    {Premi X per terminare e correggi}%
}

%% Carico la classe
\ProcessOptions\relax

%% Gestisco la selezione della formattazione
\ifthenelse{\boolean{univpm@oneside}\AND%
            \boolean{univpm@twoside}}%
{%
  \ClassError{univpmthesis}%
    {Non puoi definire due formattazioni!}%
    {Premi X per terminare e correggi l'errore!}%
}%
{\relax}

\ifthenelse{\(\NOT\boolean{univpm@oneside}\)\AND%
            \(\NOT\boolean{univpm@twoside}\)}%
{%
  \ClassError{univpmthesis}%
    {Devi definire la formattazione su pagina singola o fronte-retro!}%
    {Premi X per terminare e correggi l'errore!}%
}%
{\relax}

\ifunivpm@oneside
  \LoadClass[11pt,%
		     oneside,%
             open=right,%
             cleardoublepage=empty,%
             chapterprefix=true]{scrbook}
\fi

\ifunivpm@twoside
  \LoadClass[11pt,%
		     twoside,%
             open=right,%
             cleardoublepage=empty,%
             chapterprefix=true]{scrbook}
\fi

%% Gestisco la selezione della lingua
\ifthenelse{\boolean{univpm@english}\AND%
            \boolean{univpm@italian}}%
{%
  \ClassError{univpmthesis}%
    {Non puoi definire due lingue!}%
    {Premi X per terminare e correggi l'errore!}%
}%
{\relax}

\ifthenelse{\(\NOT\boolean{univpm@english}\)\AND%
            \(\NOT\boolean{univpm@italian}\)}%
{%
  \ClassError{univpmthesis}%
    {Devi definire una lingua!}%
    {Premi X per terminare e correggi l'errore!}%
}%
{\relax}

\typeout{**************************************************}
\ifunivpm@english\typeout{* Hai selezionato: INGLESE}\fi
\ifunivpm@italian\typeout{* Hai selezionato: ITALIANO}\fi
\typeout{**************************************************}

%% \RequirePackage[utf8]{inputenc}
%% \RequirePackage[T1]{fontenc}

\RequirePackage[english,italian]{babel}

\ifunivpm@english
  \AtBeginDocument{\selectlanguage{english}}
\fi

\ifunivpm@italian
  \AtBeginDocument{\selectlanguage{italian}}
  \RequirePackage{indentfirst}
\fi

\addto\captionsitalian{\def\acknowledgename{Ringraziamenti}}
\addto\captionsenglish{\def\acknowledgename{Acknowledgments}}

\addto\captionsitalian{\def\dedicationname{Dedica}}
\addto\captionsenglish{\def\dedicationname{Dedication}}

%% Richiedo il pacchetto per le immagini
\RequirePackage{graphicx}

%% Richiedo il pacchetto per l'interlinea
\RequirePackage{setspace}
\setstretch{1.15}

%% Imposto le dimensioni della pagina
\RequirePackage{geometry}
\geometry{%
  papersize={210mm,297mm},
  text={140mm,230mm},
  marginratio=1:1,
  bindingoffset=4mm
}
\addtolength{\footskip}{-0.5cm}
%
\RequirePackage{afterpage}

%% Carico hyperref a seconda del driver usato
\RequirePackage{ifpdf}
\ifpdf
  \RequirePackage[pdfpagelabels]{hyperref}
\else
  \RequirePackage{hyperref}
\fi
%%%%%%%%%%%% Segni per il taglio per il formato ridotto %%%%%%%%%%%%
%\ifunivpm@aquattroprint%
%  \RequirePackage[a4,
%                  center,
%                  cam]{crop}
%\fi
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Città dell'autore
\newcommand{\thlocation}[1]{\def\univpm@thlocation{#1}}
%% Data di stampa (in qualsiasi formato)
\newcommand{\thtime}[1]{\def\univpm@thtime{#1}}
%% Definizione dei comandi per le label in inglese
\newcommand{\authorlabelEN}[1]{\def\univpm@authorlabelEN{#1}}
\newcommand{\advisorlabelEN}[1]{\def\univpm@advisorlabelEN{#1}}
\newcommand{\coadvisorlabelEN}[1]{\def\univpm@coadvisorlabelEN{#1}}
%\newcommand{\curriculumadvisorlabelEN}[1]{\def\univpm@curriculumadvisorlabelEN{#1}}
%\newcommand{\directorlabelEN}[1]{\def\univpm@directorlabelEN{#1}}
\newcommand{\cyclelabelEN}[1]{\def\univpm@cyclelabelEN{#1}}
%% Label inglesi
\authorlabelEN{Candidate:}
\advisorlabelEN{Advisor:}
\coadvisorlabelEN{Coadvisor:}
%\curriculumadvisorlabelEN{Curriculum Supervisor:}
%\directorlabelEN{Ph.D. School Supervisor:}
\cyclelabelEN{Academic Year}

%% Definizione dei comandi per le label in italiano
\newcommand{\authorlabelIT}[1]{\def\univpm@authorlabelIT{#1}}
\newcommand{\advisorlabelIT}[1]{\def\univpm@advisorlabelIT{#1}}
\newcommand{\coadvisorlabelIT}[1]{\def\univpm@coadvisorlabelIT{#1}}
%\newcommand{\curriculumadvisorlabelIT}[1]{\def\univpm@curriculumadvisorlabelIT{#1}}
%\newcommand{\directorlabelIT}[1]{\def\univpm@directorlabelIT{#1}}
\newcommand{\cyclelabelIT}[1]{\def\univpm@cyclelabelIT{#1}}
%% Label italiane
\authorlabelIT{Autori:}
\advisorlabelIT{Tutor:}
\coadvisorlabelIT{Correlatore:}
%\curriculumadvisorlabelIT{Coordinatore del Curriculum:}
%\directorlabelIT{Coordinatore della Scuola di Dottorato:}
\cyclelabelIT{Anno Accademico}

%% Definizione dei comandi per le label che verranno usate
\newcommand{\authorlabel}[1]{\def\univpm@authorlabel{#1}}
\newcommand{\advisorlabel}[1]{\def\univpm@advisorlabel{#1}}
\newcommand{\coadvisorlabel}[1]{\def\univpm@coadvisorlabel{#1}}
%\newcommand{\curriculumadvisorlabel}[1]{\def\univpm@curriculumadvisorlabel{#1}}
%\newcommand{\directorlabel}[1]{\def\univpm@directorlabel{#1}}
\newcommand{\cyclelabel}[1]{\def\univpm@cyclelabel{#1}}

%% Scelgo la label giusta in base alla lingua selezionata
\ifunivpm@english%
  \authorlabel{\univpm@authorlabelEN}
  \advisorlabel{\univpm@advisorlabelEN}
  \coadvisorlabel{\univpm@coadvisorlabelEN}
  %\curriculumadvisorlabel{\univpm@curriculumadvisorlabelEN}
  %\directorlabel{\univpm@directorlabelEN}
  \cyclelabel{\univpm@cyclelabelEN}
\fi

\ifunivpm@italian%
  \authorlabel{\univpm@authorlabelIT}
  \advisorlabel{\univpm@advisorlabelIT}
  \coadvisorlabel{\univpm@coadvisorlabelIT}
  %\curriculumadvisorlabel{\univpm@curriculumadvisorlabelIT}
  %\directorlabel{\univpm@directorlabelIT}
  \cyclelabel{\univpm@cyclelabelIT}
\fi

%% Nome dell'Università
\newcommand{\univpm}[1]{\def\univpm@univpm{#1}}
\univpm{Universit\`{a} Politecnica delle Marche}
%% Indirizzo dell'Università
\newcommand{\facultyaddress}[1]{\def\univpm@facultyaddress{#1}}
\facultyaddress{Via Brecce Bianche -- 60131 Ancona (AN), Italy}
%% Logo dell'Università
\def\univpm@logo{logoUNIVPM}
%%  Nome del Corso di studi
\newcommand{\thcourse}[1]{\def\univpm@thcourse{#1}}
%%  Facoltà 
\newcommand{\thfaculty}[1]{\def\univpm@thfaculty{#1}}
%% Titolo della tesi
\newcommand{\thtitle}[1]{\def\univpm@thtitle{#1}}
%% Sotto titolo della tesi
\newcommand{\thsubtitle}[1]{\def\univpm@thsubtitle{#1}}
%% Autore della tesi
\newcommand{\thauthor}[1]{\def\univpm@thauthor{#1}}
%% Relatore
\newcommand{\thadvisor}[1]{\def\univpm@thadvisor{#1}}
%% Correlatore
\newcommand{\thcoadvisor}[3]{\def\univpm@thcoadvisor{#1 \par #2 \par #3}}


%% Comando per la gestione anno accademico
\newcommand{\ayear}[1]{\def\univpm@ayear{#1}}
%% Comando per la gestione della dedica
\newcommand{\thesisdedication}[1]%
{%
  \def\univpm@dedication{#1}
}
%% Comando per la gestione dell'hardcover
\newcommand{\hscover}%
{%
%% Logo e nomi dell'Università
  \begin{minipage}[t]{\textwidth}
    \begin{center}
      \includegraphics[scale=.8]{\univpm@logo}\par
	  \vspace{1em}
      \large{ %\small{
        %\textsc{\univpm@univpm}\par
		\textsc{\univpm@thfaculty}\par
        \textsc{\univpm@thcourse}\par
      }
      \vspace{1em}
      \hrule
    \end{center}
  \end{minipage}

  \vspace{3em}

%% Titolo
  \begin{minipage}[t]{\textwidth}
    \begin{center}
      \huge\usekomafont{title}{\univpm@thtitle}\par
      \ifdefined\univpm@thsubtitle
        \vspace{2em}
        \large\usekomafont{title}{\univpm@thsubtitle}\par
      \fi
    \end{center}
  \end{minipage}

  \vfill

%% Autore, relatore e correlatore
  \begin{minipage}[t]{\textwidth}
    \begin{flushright}
      \large{%
        \univpm@authorlabel\par
      \textbf{\univpm@thauthor}\par
      }
    \end{flushright}
    \vspace{1em}
    \univpm@advisorlabel\par
    \textbf{\univpm@thadvisor}\par
    \vspace{2em}
    \ifdefined\univpm@thcoadvisor
 	  \univpm@coadvisorlabel\par%
      \textbf{\univpm@thcoadvisor}\par
      \vspace{2em}
    \fi
  \end{minipage}

  \vspace{4em}

%% Anno Accademico
  \begin{minipage}[t]{\textwidth}
    \begin{center}
      \univpm@cyclelabel~\univpm@ayear\par
    \end{center}
  \end{minipage}
}

%% Comando per la gestione del colophon
\newcommand{\colophon}%
{%
  \hfill\vfill
  \noindent\begin{minipage}[t]{\textwidth}
    \hrule
    \vspace{1em}
    \begin{center}
      \small{
        \textsc{\univpm@univpm}\par
		\textsc{\univpm@thfaculty}\par
		\textsc{\univpm@thcourse}\par
        \univpm@facultyaddress\par
      }
    \end{center}
  \end{minipage}
}
%% Viene ridefinito il comando maketitle
\renewcommand*\maketitle{%
%% Doppia pagina vuota
%  \hfill\vfill
%  \cleardoublepage\thispagestyle{empty}

%% Hardcover e pagina vuota
  \thispagestyle{empty}
  \ifpdf\pdfbookmark{Hardcover}{Hardcover}\fi
  \afterpage{%
  \newgeometry{text={140mm,230mm},
  marginratio=1:1}
  \centering
  \hscover
  \restoregeometry
  }
  \cleardoublepage\thispagestyle{empty}
%% Softcover e colophon
  \ifpdf\pdfbookmark{Softcover}{Softcover}\fi
  \hscover
  \clearpage\thispagestyle{empty}
  \colophon
%% Dedica, se presente
  \ifdefined\univpm@dedication
    \cleardoublepage\thispagestyle{empty}
    \ifpdf\pdfbookmark{\dedicationname}{\dedicationname}\fi
    \hfill\vfill
    \begin{flushright}
      \large\textit{\univpm@dedication}
    \end{flushright}
    \vfill
  \fi
}

%% Viene ridefinito il comando maketitle
\newcommand*\makesofttitle{%
%% Doppia pagina vuota
%  \hfill\vfill
%  \cleardoublepage\thispagestyle{empty}

%% Hardcover e pagina vuota
  \thispagestyle{empty}
  \ifpdf\pdfbookmark{Hardcover}{Hardcover}\fi
  \afterpage{%
  \newgeometry{text={140mm,230mm},
  marginratio=1:1}
  \centering
  \hscover
  \restoregeometry
  }
  \cleardoublepage\thispagestyle{empty}
  
}
%% Ambiente per gestire i ringraziamenti
\newenvironment{thesisacknowledge}[1][]%
{%
%% In base alla lingua selezionata creo titolo e testo
%%  \selectlanguage{#1}
  \ifblank{#1}{}{\begin{otherlanguage}{#1}}
    \chapter*{\acknowledgename}
    \ifpdf
      \pdfbookmark{\acknowledgename}{\acknowledgename}
    \fi
  \ifblank{#1}{}{\end{otherlanguage}}
}%
{%
%% Stampo data e firma dell'autore
    \ifdefined\univpm@thlocation
      \ifdefined\univpm@thtime
        \bigskip\par
        \noindent\textit{\univpm@thlocation, \univpm@thtime}\par
        \hfill\univpm@thauthor\par
      \else
        \ClassError{univpmthesis}%
          {Devi definire la data di stampa!}%
          {Premi X per terminare e correggi l'errore!}%
      \fi
    \else
      \ClassError{univpmthesis}%
        {Devi definire il luogo di stampa!}%
        {Premi X per terminare e correggi l'errore!}%
    \fi
%% Ripristino la lingua
%%  \ifunivpm@english
%%    \selectlanguage{english}
%%  \fi

%%  \ifunivpm@italian
%%    \selectlanguage{italian}
%%  \fi
}
%% Ambiente per gestire l'abstract
\newenvironment{thesisabstract}[1][]%
{%
%% In base alla lingua selezionata creo titolo e testo
%%  \selectlanguage{#1}
  \ifblank{#1}{}{\begin{otherlanguage}{#1}}
    \chapter*{\abstractname}
    \ifpdf\pdfbookmark{\abstractname}{\abstractname}\fi
  \ifblank{#1}{}{\end{otherlanguage}}
}
{%
%% Ripristino la lingua
%%  \ifunivpm@english
%%    \selectlanguage{english}
%%  \fi

%%  \ifunivpm@italian
%%    \selectlanguage{italian}
%%  \fi
\relax}
%% Ambiente per gestire i ringraziamenti
\newcommand{\thesistoc}%
{%
  \cleardoublepage
  \ifpdf\pdfbookmark{\contentsname}{\contentsname}\fi
  \tableofcontents

  \ifunivpm@lof%
    \cleardoublepage
    \ifpdf\pdfbookmark{\listfigurename}{\listfigurename}\fi
    \listoffigures
  \fi

  \ifunivpm@lot%
    \cleardoublepage
    \ifpdf\pdfbookmark{\listtablename}{\listtablename}\fi
    \listoftables
  \fi
}

\endinput
%%
%% End of file `univpmthesis.cls'.
