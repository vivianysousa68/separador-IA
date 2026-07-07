import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

try:
    import mysql.connector
except ImportError:
    mysql = None

try:
    from pedalboard import Pedalboard, Compressor, HighpassFilter, Gain, Limiter, HighShelfFilter, LowShelfFilter
    from pedalboard.io import AudioFile
    import numpy as np
    PEDALBOARD_DISPONIVEL = True
except ImportError:
    PEDALBOARD_DISPONIVEL = False

USUARIO_CADASTRADO = "admin"
SENHA_CADASTRADA = "1234"

COR_BG_PRINCIPAL = "#0f0f11"
COR_BG_CARD = "#16161a"
COR_BG_DROPZONE = "#121215"
COR_TEXTO = "#ffffff"
COR_TEXTO_MUTED = "#71717a"
COR_VERDE = "#4ade80"
COR_BORDA = "#27272a"

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_MODIFICADOS = os.path.join(DIRETORIO_BASE, "Modificados")
PASTA_MASTERIZADOS = os.path.join(DIRETORIO_BASE, "Masterizados")

os.makedirs(PASTA_MODIFICADOS, exist_ok=True)
os.makedirs(PASTA_MASTERIZADOS, exist_ok=True)

def conectar_banco():
    if mysql is None:
        raise ImportError("mysql-connector-python não está instalado.")
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="separador",
    )

def salvar_status_inicial(arquivo):
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        comando_sql = "INSERT INTO processamentos (nome_musica, caminho, status) VALUES (%s, %s, %s)"
        nome_arquivo = os.path.basename(arquivo)
        cursor.execute(comando_sql, (nome_arquivo, arquivo, "Processando"))
        conexao.commit()
        id_registro = cursor.lastrowid
        cursor.close()
        conexao.close()
        return id_registro
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível gravar no banco de dados: {e}")
        return None

def atualizar_status_final(id_registro, novo_status):
    if id_registro is None:
        return
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        comando_sql = "UPDATE processamentos SET status = %s WHERE id = %s"
        cursor.execute(comando_sql, (novo_status, id_registro))
        conexao.commit()
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"⚠️ Erro ao atualizar o banco de dados: {e}")

def atualizar_progresso(valor):
    progresso_var.set(valor)
    rotulo_progresso.config(text=f"Progresso: {valor}%")
    janela.update_idletasks()

def separar_audio(caminho_da_musica):
    if not os.path.exists(caminho_da_musica):
        messagebox.showerror("Erro", f"O arquivo '{caminho_da_musica}' não foi encontrado.")
        return

    id_db = salvar_status_inicial(caminho_da_musica)

    comando = [
        sys.executable, "-m", "demucs", "-n", "htdemucs", "-j", "4",
        "--mp3", "--two-stems=vocals", caminho_da_musica,
    ]

    try:
        processo = subprocess.Popen(
            comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )

        atualizar_progresso(0)

        for linha in processo.stdout:
            print(linha, end="")
            if "100%" in linha:
                atualizar_progresso(100)
            else:
                match = re.search(r"(\d{1,3})%", linha)
                if match:
                    percentual_atual = min(int(match.group(1)), 99)
                    atualizar_progresso(percentual_atual)

        retorno = processo.wait()

        if retorno == 0:
            atualizar_progresso(100)
            messagebox.showinfo("Sucesso", "Concluído com sucesso!")
            atualizar_status_final(id_db, "Concluído")
        else:
            messagebox.showerror("Erro", "Ocorreu um erro no processamento do Demucs.")
            atualizar_status_final(id_db, "Erro")

    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao processar: {e}")
        atualizar_status_final(id_db, "Erro")

def processar_arquivo():
    caminho = caminho_var.get().strip().strip('"').strip("'")
    if not caminho or caminho == "Nenhum arquivo selecionado":
        messagebox.showerror("Erro", "Selecione um arquivo primeiro clicando na área acima.")
        return

    btn_processar.config(state="disabled", text="⚡ Processando...")
    lbl_selecionar.config(text="Processando arquivo...")

    def liberar_botao():
        btn_processar.config(state="normal", text="✨ Começar Processamento")
        lbl_selecionar.config(text="Selecione um arquivo")
        caminho_var.set("Nenhum arquivo selecionado")

    threading.Thread(target=lambda: [separar_audio(caminho), liberar_botao()], daemon=True).start()

def escolher_arquivo():
    caminho = filedialog.askopenfilename(
        title="Selecione o arquivo de áudio",
        filetypes=[("Arquivos de áudio", "*.mp3 *.wav *.m4a *.flac")]
    )
    if caminho:
        caminho_var.set(caminho)
        lbl_selecionar.config(text=f"Selecionado: {os.path.basename(caminho)}")

def verificar_login():
    usuario = entry_usuario.get().strip()
    senha = entry_senha.get().strip()

    if usuario == USUARIO_CADASTRADO and senha == SENHA_CADASTRADA:
        frame_login.pack_forget()
        montar_tela_principal()
    else:
        messagebox.showerror("Login inválido", "Usuário ou senha incorretos.")

def alternar_senha():
    if entry_senha.cget("show") == "*":
        entry_senha.config(show="")
        btn_mostrar_senha.config(text="Ocultar senha")
    else:
        entry_senha.config(show="*")
        btn_mostrar_senha.config(text="Mostrar senha")

def abrir_janela_efeitos():
    caminho_original = caminho_var.get().strip().strip('"').strip("'")
    if not caminho_original or not os.path.exists(caminho_original):
        messagebox.showerror("Erro", "Selecione um arquivo de áudio válido primeiro.")
        return

    janela_efeitos = tk.Toplevel(janela)
    janela_efeitos.title("Alterar Tom ou Tempo")
    janela_efeitos.geometry("400x300")
    janela_efeitos.configure(bg=COR_BG_PRINCIPAL)
    janela_efeitos.resizable(False, False)
    janela_efeitos.transient(janela)
    janela_efeitos.grab_set()

    tk.Label(janela_efeitos, text="Modificar Áudio", font=("Arial", 14, "bold"), bg=COR_BG_PRINCIPAL, fg=COR_TEXTO).pack(pady=10)

    tk.Label(janela_efeitos, text="Velocidade (ex: 1.0 = normal):", bg=COR_BG_PRINCIPAL, fg=COR_TEXTO_MUTED).pack()
    escala_velocidade = tk.Scale(janela_efeitos, from_=0.5, to=2.0, resolution=0.1, orient="horizontal", length=300, bg=COR_BG_PRINCIPAL, fg=COR_TEXTO, highlightthickness=0)
    escala_velocidade.set(1.0)
    escala_velocidade.pack(pady=5)

    tk.Label(janela_efeitos, text="Tom (Semitons):", bg=COR_BG_PRINCIPAL, fg=COR_TEXTO_MUTED).pack()
    escala_tom = tk.Scale(janela_efeitos, from_=-6, to=6, resolution=1, orient="horizontal", length=300, bg=COR_BG_PRINCIPAL, fg=COR_TEXTO, highlightthickness=0)
    escala_tom.set(0)
    escala_tom.pack(pady=5)

    def aplicar_efeitos():
        vel = escala_velocidade.get()
        tom_semitons = escala_tom.get()

        nome_completo = os.path.basename(caminho_original)
        nome, ext = os.path.splitext(nome_completo)

        contador = 1
        while True:
            nome_saida = f"{contador}_modificado_{nome}{ext}"
            arquivo_saida = os.path.join(PASTA_MODIFICADOS, nome_saida)
            if not os.path.exists(arquivo_saida):
                break
            contador += 1

        fator_tom = 2 ** (tom_semitons / 12.0)
        sample_rate_alvo = int(44100 * fator_tom)
        velocidade_ajustada = vel / fator_tom

        comando_ffmpeg = [
            "ffmpeg", "-y", "-i", caminho_original,
            "-filter_complex", f"asetrate={sample_rate_alvo},atempo={velocidade_ajustada}",
            arquivo_saida
        ]

        id_db = salvar_status_inicial(caminho_original)

        def rodar_ffmpeg():
            try:
                btn_salvar.config(state="disabled", text="Processando...")
                processo = subprocess.run(comando_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if processo.returncode == 0:
                    messagebox.showinfo("Sucesso", f"Salvo na pasta Modificados como:\n{nome_saida}")
                    atualizar_status_final(id_db, "Concluído (Efeitos)")
                    janela_efeitos.destroy()
                else:
                    messagebox.showerror("Erro", f"Erro no FFmpeg:\n{processo.stderr}")
                    atualizar_status_final(id_db, "Erro (Efeitos)")
                    btn_salvar.config(state="normal", text="Salvar Novo Áudio")
            except FileNotFoundError:
                messagebox.showerror("Erro", "FFmpeg não foi encontrado no sistema.")
                atualizar_status_final(id_db, "Erro (FFmpeg Ausente)")
                btn_salvar.config(state="normal", text="Salvar Novo Áudio")

        threading.Thread(target=rodar_ffmpeg, daemon=True).start()

    btn_salvar = tk.Button(janela_efeitos, text="Salvar Novo Áudio", width=22, bg=COR_VERDE, fg="#000000", font=("Arial", 10, "bold"), command=aplicar_efeitos, relief="flat")
    btn_salvar.pack(pady=20)

def abrir_janela_masterizacao():
    if not PEDALBOARD_DISPONIVEL:
        messagebox.showerror("Dependência Ausente", "Para masterizar, instale as bibliotecas:\npip install pedalboard numpy")
        return

    caminho_original = caminho_var.get().strip().strip('"').strip("'")
    if not caminho_original or not os.path.exists(caminho_original):
        messagebox.showerror("Erro", "Selecione um arquivo de áudio válido na tela principal primeiro.")
        return

    janela_master = tk.Toplevel(janela)
    janela_master.title("Masterização Inteligente por IA")
    janela_master.geometry("400x320")
    janela_master.configure(bg=COR_BG_PRINCIPAL)
    janela_master.resizable(False, False)
    janela_master.transient(janela)
    janela_master.grab_set()

    tk.Label(janela_master, text="Masterização Inteligente", font=("Arial", 14, "bold"), bg=COR_BG_PRINCIPAL, fg=COR_TEXTO).pack(pady=15)
    tk.Label(janela_master, text="Escolha a intensidade da masterização:", bg=COR_BG_PRINCIPAL, fg=COR_TEXTO_MUTED).pack(pady=5)

    intensidade_var = tk.StringVar(value="Comercial (Streaming)")
    combo_estilo = ttk.Combobox(janela_master, textvariable=intensidade_var, values=["Suave (Jazz/Acústico)", "Comercial (Streaming)", "Intensa (Club/Eletro)"], state="readonly", width=25)
    combo_estilo.pack(pady=10)

    lbl_status_master = tk.Label(janela_master, text="Pronto para processar", font=("Arial", 9, "italic"), bg=COR_BG_PRINCIPAL, fg=COR_TEXTO_MUTED)
    lbl_status_master.pack(pady=10)

    def executar_masterizacao():
        estilo = intensidade_var.get()
        nome_completo = os.path.basename(caminho_original)
        nome, ext = os.path.splitext(nome_completo)

        contador = 1
        while True:
            nome_saida = f"{contador}_Master_{nome}{ext}"
            arquivo_saida = os.path.join(PASTA_MASTERIZADOS, nome_saida)
            if not os.path.exists(arquivo_saida):
                break
            contador += 1

        btn_disparar.config(state="disabled", text="Masterizando...")
        lbl_status_master.config(text="Analisando dinâmica e aplicando DSP...", fg=COR_VERDE)

        id_db = salvar_status_inicial(caminho_original)

        def rodar_dsp():
            try:
                with AudioFile(caminho_original) as f:
                    audio_dados = f.read(f.frames)
                    sr = f.samplerate

                rms_volume = np.sqrt(np.mean(audio_dados**2))

                if estilo == "Suave (Jazz/Acústico)":
                    thresh = -15.0 if rms_volume > 0.1 else -12.0
                    comp_ratio = 2.5
                    ganho_compensacao = 1.5
                    graves_db = 4.0
                    brilho_db = -5.0
                    limite_teto = -1.0
                elif estilo == "Comercial (Streaming)":
                    thresh = -20.0 if rms_volume > 0.1 else -16.0
                    comp_ratio = 4.0
                    ganho_compensacao = 4.5
                    graves_db = -3.0
                    brilho_db = 3.5
                    limite_teto = -0.3
                else:
                    thresh = -24.0 if rms_volume > 0.1 else -20.0
                    comp_ratio = 6.0
                    ganho_compensacao = 6.0
                    graves_db = 2.0
                    brilho_db = 3.0
                    limite_teto = -0.1

                board = Pedalboard([
                    HighpassFilter(cutoff_frequency_hz=30),
                    Compressor(threshold_db=thresh, ratio=comp_ratio, attack_ms=15, release_ms=150),
                    LowShelfFilter(cutoff_frequency_hz=200 if estilo == "Suave (Jazz/Acústico)" else 250, gain_db=graves_db),
                    HighShelfFilter(cutoff_frequency_hz=5000 if estilo == "Suave (Jazz/Acústico)" else 7000, gain_db=brilho_db),
                    Gain(gain_db=ganho_compensacao),
                    Limiter(threshold_db=limite_teto, release_ms=80)
                ])

                audio_processado = board(audio_dados, sr)

                with AudioFile(arquivo_saida, 'w', sr, audio_processado.shape[0]) as f:
                    f.write(audio_processado)

                messagebox.showinfo("Sucesso!", f"Música masterizada salva na pasta Masterizados:\n{nome_saida}")
                atualizar_status_final(id_db, f"Concluído (Master: {estilo})")
                janela_master.destroy()

            except Exception as ex:
                messagebox.showerror("Erro", f"Erro ao masterizar o arquivo:\n{ex}")
                atualizar_status_final(id_db, "Erro (Masterização)")
                btn_disparar.config(state="normal", text="✨ Iniciar Masterização")
                lbl_status_master.config(text="Falha no processamento", fg="red")

        threading.Thread(target=rodar_dsp, daemon=True).start()

    btn_disparar = tk.Button(janela_master, text="✨ Iniciar Masterização", width=22, bg=COR_VERDE, fg="#000000", font=("Arial", 10, "bold"), command=executar_masterizacao, relief="flat", cursor="hand2")
    btn_disparar.pack(pady=15)

def montar_tela_principal():
    global lbl_selecionar, progresso_var, rotulo_progresso, btn_processar

    janela.geometry("1000x500")
    janela.configure(bg=COR_BG_PRINCIPAL)

    container_corpo = tk.Frame(janela, bg=COR_BG_PRINCIPAL)
    container_corpo.pack(fill="both", expand=True, padx=40, pady=40)

    card_esquerdo = tk.Frame(container_corpo, bg=COR_BG_CARD, bd=0, highlightbackground=COR_BORDA, highlightthickness=1)
    card_esquerdo.pack(side="left", fill="both", expand=True, padx=(0, 20))

    tk.Label(card_esquerdo, text="Remova os vocais de qualquer música", font=("Arial", 15, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO).pack(anchor="w", padx=25, pady=(25, 2))
    tk.Label(card_esquerdo, text="Ajudaremos você a fazer uma versão HQ karaoke!", font=("Arial", 10), bg=COR_BG_CARD, fg=COR_TEXTO_MUTED).pack(anchor="w", padx=25, pady=(0, 25))

    btn_dropzone = tk.Button(card_esquerdo, bg=COR_BG_DROPZONE, activebackground=COR_BG_DROPZONE, bd=0, highlightbackground=COR_BORDA, highlightthickness=1, command=escolher_arquivo, relief="flat")
    btn_dropzone.pack(fill="both", expand=True, padx=25, pady=(0, 15))

    frame_interno_drop = tk.Frame(btn_dropzone, bg=COR_BG_DROPZONE)
    frame_interno_drop.pack(expand=True)

    lbl_icone = tk.Label(frame_interno_drop, text="📁↑", font=("Arial", 28), bg=COR_BG_DROPZONE, fg=COR_VERDE)
    lbl_icone.pack(side="left", padx=10)

    lbl_selecionar = tk.Label(frame_interno_drop, text="Selecione um arquivo", font=("Arial", 13), bg=COR_BG_DROPZONE, fg=COR_TEXTO)
    lbl_selecionar.pack(side="left", padx=10)

    COR_HOVER = "#1c1c21"

    btn_processar = tk.Button(card_esquerdo, text="✨ Começar Processamento", bg=COR_VERDE, fg="#000000", font=("Arial", 11, "bold"), activebackground="#3cd073", activeforeground="#000000", bd=0, relief="flat", command=processar_arquivo, cursor="hand2")
    btn_processar.pack(fill="x", padx=25, pady=(0, 15), ipady=8)

    progresso_var = tk.IntVar(value=0)
    style = ttk.Style()
    style.theme_use('default')
    style.configure("Custom.Horizontal.TProgressbar", thickness=4, troughcolor=COR_BG_PRINCIPAL, background=COR_VERDE, bordercolor=COR_BG_PRINCIPAL)

    bar_progresso = ttk.Progressbar(card_esquerdo, orient="horizontal", mode="determinate", variable=progresso_var, style="Custom.Horizontal.TProgressbar")
    bar_progresso.pack(fill="x", padx=25, pady=(0, 5))

    rotulo_progresso = tk.Label(card_esquerdo, text="", font=("Arial", 8), bg=COR_BG_CARD, fg=COR_TEXTO_MUTED)
    rotulo_progresso.pack(anchor="e", padx=25, pady=(0, 10))

    card_direito = tk.Frame(container_corpo, bg=COR_BG_CARD, width=280, bd=0, highlightbackground=COR_BORDA, highlightthickness=1)
    card_direito.pack(side="right", fill="y")
    card_direito.pack_propagate(False)

    tk.Label(card_direito, text="Outros Serviços", font=("Arial", 13, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO).pack(anchor="w", padx=20, pady=(25, 15))

    tk.Button(card_direito, text="🪄   Masterização IA Inteligente", bg=COR_BG_CARD, fg=COR_TEXTO_MUTED, activebackground="#1f1f23", activeforeground=COR_TEXTO, bd=0, anchor="w", font=("Arial", 10), command=abrir_janela_masterizacao, cursor="hand2").pack(fill="x", padx=10, pady=4, ipady=6)

    tk.Button(card_direito, text="🎛️ Alterar Tom ou Tempo", bg=COR_BG_CARD, fg=COR_TEXTO_MUTED, activebackground="#1f1f23", activeforeground=COR_TEXTO, bd=0, anchor="w", font=("Arial", 10), command=abrir_janela_efeitos, cursor="hand2").pack(fill="x", padx=10, pady=4, ipady=6)

janela = tk.Tk()
janela.title("UVR Online - Login")
janela.geometry("400x320")
janela.configure(bg=COR_BG_PRINCIPAL)
janela.resizable(False, False)

caminho_var = tk.StringVar(value="Nenhum arquivo selecionado")

frame_login = tk.Frame(janela, bg=COR_BG_CARD, bd=0, highlightbackground=COR_BORDA, highlightthickness=1)
frame_login.pack(fill="both", expand=True, padx=40, pady=40)

tk.Label(frame_login, text="ENTRAR NA PLATAFORMA", font=("Arial", 12, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO).pack(pady=(20, 15))

tk.Label(frame_login, text="Usuário:", bg=COR_BG_CARD, fg=COR_TEXTO_MUTED).pack(anchor="w", padx=30)
entry_usuario = tk.Entry(frame_login, width=30, bg="#27272a", fg=COR_TEXTO, insertbackground=COR_TEXTO, bd=1, relief="solid")
entry_usuario.pack(pady=(0, 10))

tk.Label(frame_login, text="Senha:", bg=COR_BG_CARD, fg=COR_TEXTO_MUTED).pack(anchor="w", padx=30)
entry_senha = tk.Entry(frame_login, width=30, show="*", bg="#27272a", fg=COR_TEXTO, insertbackground=COR_TEXTO, bd=1, relief="solid")
entry_senha.pack(pady=(0, 5))

btn_mostrar_senha = tk.Button(frame_login, text="Mostrar senha", font=("Arial", 8), bg=COR_BG_CARD, fg=COR_TEXTO_MUTED, bd=0, command=alternar_senha, activebackground=COR_BG_CARD, activeforeground=COR_TEXTO)
btn_mostrar_senha.pack(pady=(0, 15))

btn_entrar = tk.Button(frame_login, text="Entrar", width=25, bg=COR_VERDE, fg="#000000", font=("Arial", 10, "bold"), command=verificar_login, relief="flat")
btn_entrar.pack(pady=5)

janela.mainloop()
