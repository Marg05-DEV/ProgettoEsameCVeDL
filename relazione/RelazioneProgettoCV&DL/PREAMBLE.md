Questo template prevede i seguenti file:
- Preambolo
```
\usepackage[tmargin=2cm,rmargin=1in,lmargin=1in,margin=0.85in,bmargin=2cm,footskip=.2in]{geometry}
\usepackage[italian]{babel}
\usepackage{amsmath,amsfonts,amsthm,amssymb,mathtools}
\usepackage[varbb]{newpxmath}
\usepackage{xfrac}
\usepackage[makeroom]{cancel}
\usepackage{mathtools}
\usepackage{bookmark}
\usepackage{enumitem}
\usepackage{imakeidx}    % gestione indice
\usepackage{hyperref,theoremref}
\hypersetup{
	pdftitle={assignment},
	colorlinks=true, linkcolor=doc!90,
	bookmarksnumbered=true,
	bookmarksopen=true
}
\usepackage[most,many,breakable]{tcolorbox}
\usepackage{xcolor}
\usepackage{varwidth}
\usepackage{varwidth}
\usepackage{etoolbox}
%\usepackage{authblk}
\usepackage{nameref}
\usepackage{multicol,array}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{booktabs}
\usepackage[ruled,vlined,linesnumbered]{algorithm2e}
\usepackage{comment} % enables the use of multi-line comments (\ifx \fi) 
\usepackage{import}
\usepackage{xifthen}
\usepackage{pdfpages}
\usepackage{transparent}
\usepackage{chngcntr}
\usepackage{tikz}
\usepackage{titletoc}
\usepackage{silence}
\WarningFilter{latexfont}{Font shape}
\WarningFilter{latexfont}{Size substitutions}
\hbadness=10000
\vbadness=10000
\hfuzz=20pt
\vfuzz=20pt
\tracinglostchars=0
\usepackage{wrapfig}
\usepackage{listingsutf8}
\usepackage{cancel}
\usepackage{mathrsfs}

\lstset{
  keywordstyle=\color{blue},       % keyword style
  commentstyle=\color{green},
  literate=
        {è}{{\`e}}1
        {à}{{\`a}}1
        {é}{{\'e}}1
        {ò}{{\`o}}1
        {ì}{{\`i}}1
        {ù}{{\`u}}1
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% SELF MADE COLORS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\definecolor{doc}{RGB}{0,60,110}
\definecolor{myg}{RGB}{56, 140, 70}
\definecolor{myb}{RGB}{45, 111, 177}
\definecolor{myr}{RGB}{199, 68, 64}
\definecolor{mytheorembg}{HTML}{F2F2F9}
\definecolor{mytheoremfr}{HTML}{00007B}
\definecolor{mylemmabg}{HTML}{FFFAF8}
\definecolor{mylemmafr}{HTML}{983b0f}
\definecolor{mypropbg}{HTML}{f2fbfc}
\definecolor{mypropfr}{HTML}{191971}
\definecolor{myexamplebg}{HTML}{F2FBF8}
\definecolor{myexamplefr}{HTML}{88D6D1}
\definecolor{myexampleti}{HTML}{2A7F7F}
\definecolor{mydefinitbg}{HTML}{E5E5FF}
\definecolor{mydefinitfr}{HTML}{3F3FA3}
\definecolor{notesgreen}{RGB}{0,162,0}
\definecolor{myp}{RGB}{197, 92, 212}
\definecolor{mygr}{HTML}{2C3338}
\definecolor{myred}{RGB}{127,0,0}
\definecolor{myyellow}{RGB}{169,121,69}
\definecolor{myexercisebg}{HTML}{F2FBF8}
\definecolor{myexercisefg}{HTML}{88D6D1}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% TCOLORBOX SETUPS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\input{tools/tcolorboxes} 
% nel file tcolorboxes vengono definiti i box grafici per i comandi successivi (teoremi, definizioni, esempi, ...)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% SELF MADE COMMANDS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand{\thm}[2]{
	\index[thmindex]{#1}
	\begin{Theorem}{#1}{}#2\end{Theorem}
}

\newcommand{\thms}[2]{
	\index[thmindex]{#1}
	\begin{theorem}{#1}{}#2\end{theorem}
}

\newcommand{\cor}[2]{\begin{Corollary}{#1}{}#2\end{Corollary}}
\newcommand{\cors}[2]{\begin{corollary}{#1}{}#2\end{corollary}}
\newcommand{\mlemma}[2]{\begin{Lemma}{#1}{}#2\end{Lemma}}
\newcommand{\mer}[2]{\begin{Exercise}{#1}{}#2\end{Exercise}}
\newcommand{\mprop}[2]{\begin{Prop}{#1}{}#2\end{Prop}}
\newcommand{\mprops}[2]{\begin{prop}{#1}{}#2\end{prop}}
\newcommand{\clm}[3]{\begin{claim}{#1}{#2}#3\end{claim}}
\newcommand{\wc}[2]{\begin{wconc}{#1}{}\setlength{\parindent}{1cm}#2\end{wconc}}
\newcommand{\thmcon}[1]{\begin{Theoremcon}{#1}\end{Theoremcon}}

\newcommand{\ex}[2]{\begin{Example}{#1}{}#2\end{Example}}
\newcommand{\exmpls}[2]{\begin{example}{#1}{}#2\end{example}}

\newcommand{\dfn}[2]{
	\index[dfnindex]{#1}
	\begin{Definition}[colbacktitle=red!75!black]{#1}{}#2\end{Definition}
	}
\newcommand{\dfns}[2]{
	\index[dfnindex]{#1}
	\begin{definition}[colbacktitle=red!75!black]{#1}{}#2\end{definition}
	}

\newcommand{\qs}[2]{\begin{question}{#1}{}#2\end{question}}

\newcommand{\pf}[2]{
	\index[pfindex]{#1}
	\begin{myproof}#2\end{myproof}}

\newcommand{\nt}[1]{\begin{note}#1\end{note}}

\newcommand{\prim}[2]{\begin{problema}[#1]#2\end{problema}}
\newcommand{\dual}[2]{\begin{duale_box}[#1]#2\end{duale_box}}


\newcommand{\mclm}[2]{\begin{myclaim}[#1]#2\end{myclaim}}
\newenvironment{myclaim}[1][\claimname]{\proof[\bfseries #1: ]}{}
\newenvironment{iclaim}[1][\claimname]{\bfseries #1\mdseries:}{}
\newcommand{\iclm}[2]{\begin{iclaim}[#1]#2\end{iclaim}}


% ===========================================================
% INDICI
% ===========================================================
\makeindex[name=thmindex, title=Indice dei Teoremi, intoc]
\makeindex[name=dfnindex, title=Indice delle Definizioni, intoc]
\makeindex[name=qsindex, title=Indice degli Esercizi, intoc]
\makeindex[name=pfindex, title=Indice delle Dimostrazioni, intoc]

```

- Macros/shortcut a comandi spesso utilizzati
```
\newcommand{\eps}{\epsilon}
\newcommand{\veps}{\varepsilon}
\newcommand{\Qed}{\begin{flushright}\qed\end{flushright}}

\newcommand{\parinn}{\setlength{\parindent}{1cm}}
\newcommand{\parinf}{\setlength{\parindent}{0cm}}

% \newcommand{\norm}{\|\cdot\|}
\newcommand{\inorm}{\norm_{\infty}}
\newcommand{\opensets}{\{V_{\alpha}\}_{\alpha\in I}}
\newcommand{\oset}{V_{\alpha}}
\newcommand{\opset}[1]{V_{\alpha_{#1}}}
\newcommand{\lub}{\text{lub}}
\newcommand{\del}[2]{\frac{\partial #1}{\partial #2}}
\newcommand{\Del}[3]{\frac{\partial^{#1} #2}{\partial^{#1} #3}}
\newcommand{\deld}[2]{\dfrac{\partial #1}{\partial #2}}
\newcommand{\Deld}[3]{\dfrac{\partial^{#1} #2}{\partial^{#1} #3}}
\newcommand{\der}[2]{\frac{\mathrm{d} #1}{\mathrm{d} #2}}
% \newcommand{\ddd}[3]{\frac{\mathrm{d}^{#3} #1}{\mathrm{d}^{#3} #2}}
\newcommand{\lm}{\lambda}
\newcommand{\uin}{\mathbin{\rotatebox[origin=c]{90}{$\in$}}}
\newcommand{\usubset}{\mathbin{\rotatebox[origin=c]{90}{$\subset$}}}
\newcommand{\lt}{\left}
\newcommand{\rt}{\right}
\newcommand{\bs}[1]{\boldsymbol{#1}}
\newcommand{\exs}{\exists}
\newcommand{\st}{\strut}
\newcommand{\dps}[1]{\displaystyle{#1}}
\newcommand{\id}{\text{id}}

\newcommand{\sess}{\underline{se e solo se} }
\newcommand{\non}{\underline{non} }
\newcommand{\Non}{\underline{Non} }

\newcommand{\ul}[1]{\underline{#1}}
\newcommand{\U}[1]{\underline{#1}}
\newcommand{\bl}[1]{\textbf{#1}}
\newcommand{\B}[1]{\textbf{#1}}
\newcommand{\itl}[1]{\textit{#1}}
\newcommand{\I}[1]{\textit{#1}}

\newcommand{\affianca}[2]{
    \begin{minipage}{0.45\textwidth}
        #1
    \end{minipage}
    \hfill
    \begin{minipage}{0.45\textwidth}
        #2
    \end{minipage}
}

\newcommand{\myaffianca}[4]{
    \begin{minipage}{#1\textwidth}
        #2
    \end{minipage}
    \hfill
    \begin{minipage}{#3\textwidth}
        #4
    \end{minipage}
}

\newcommand{\triaffianca}[3]{
    \begin{minipage}{0.3\textwidth}
        #1
    \end{minipage}
    \hfill
    \begin{minipage}{0.3\textwidth}
        #2
    \end{minipage}
    \hfill
    \begin{minipage}{0.3\textwidth}
        #3
    \end{minipage}
}

\newcommand{\image}[2]{
    \smallskip
    \centering
    \includegraphics[width=#1\textwidth]{#2}
    \smallskip }

\newcommand{\tabimage}[2]{
    \includegraphics[width=#1\textwidth]{#2}
}

\newcommand{\e}{È }

\newcommand{\sol}{\setlength{\parindent}{0cm}\textbf{\textit{Solution:}}\setlength{\parindent}{1cm} }
\newcommand{\solve}[1]{\setlength{\parindent}{0cm}\textbf{\textit{Solution: }}\setlength{\parindent}{1cm}#1 \Qed}

\newcommand{\qssol}[2]{
	&\index[qsindex]{#1}
    \qs{}{\bl{#1} \\[6pt] \sol #2}}

\newcommand{\qssolp}[3]{
	%\index[qsindex]{#2}
    \qs{}{#1 \\[6pt] \bl{#2} \\[6pt] \sol #3}}

\newcommand{\qspf}[3]{
  %\phantomsection
	%\index[qsindex]{#1|hyperpage}
    \qs{}{\B{#1} \\[0.5pt] \pf{#2}{#3}}}

\newcommand{\p}[1]{
    
    \noindent 
    #1}

```

- Letterfonts (shortcut a font di lettere utilizzabili in math mode su LaTeX)
```
% number sets
\newcommand{\RR}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{R}}{\mathbb{R}^{#1}}}}
\newcommand{\NN}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{N}}{\mathbb{N}^{#1}}}}
\newcommand{\ZZ}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{Z}}{\mathbb{Z}^{#1}}}}
\newcommand{\QQ}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{Q}}{\mathbb{Q}^{#1}}}}
\newcommand{\CC}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{C}}{\mathbb{C}^{#1}}}}
\newcommand{\PP}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{P}}{\mathbb{P}^{#1}}}}
\newcommand{\HH}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{H}}{\mathbb{H}^{#1}}}}
\newcommand{\FF}[1][]{\ensuremath{\ifstrempty{#1}{\mathbb{F}}{\mathbb{F}^{#1}}}}
% expected value
\newcommand{\EE}{\ensuremath{\mathbb{E}}}

% Other shortcut commands for letter font that are unused
```