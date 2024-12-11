from flask import Flask,render_template,request,url_for,redirect,session,flash,jsonify,send_file
from flask_mysqldb import MySQL
import json 
import config
import pandas as pd
import io
import matplotlib.pyplot as plt
import base64
import qrcode
import openpyxl

app=Flask(__name__)

#se conectan los parametros de conectividad
app.config["MYSQL_HOST"]=config.MYSQL_HOSTNAME
app.config["MYSQL_USER"]=config.MYSQL_USER
app.config["MYSQL_PASSWORD"]=config.MYSQL_PASSWORD
app.config["MYSQL_DB"]=config.MYSQL_DB
app.config["SECRET_KEY"]=config.SECRET_KEY 

mysql=MySQL(app) #conecta con la base de datos

def requiere_login(f):
    def wrap(*args,**kwargs): 
        if "usuario" in session:
            return f(*args,**kwargs) 
        else:
            flash("Primero tenes que loguearte","ERROR")
            return redirect(url_for("login"))
    wrap.__name__=f.__name__ 
    return wrap

def verificar_id_tarea(tarea_id):
        cur=mysql.connection.cursor()
        cur.execute(f"SELECT * FROM `tareas` WHERE tarea_id={tarea_id}")
        tarea=cur.fetchone()
        
        cur.close()
        return tarea[5]

def requiere_admin(f): 
    def wrap(*args,**kwargs): 
        if session["rol"]==1 or session["rol"]==3: 
            return f(*args,**kwargs) 
        else:
            flash("No podes acceder","PROHIBIDO")
            return redirect(url_for("listado"))
    wrap.__name__=f.__name__ 
    return wrap

def requiere_creador(f): 
    def wrap(*args,**kwargs): 
        if session["rol"]==3: 
            return f(*args,**kwargs) 
        else:
            flash("No podes acceder","PROHIBIDO")
            return redirect(url_for("listado"))
    wrap.__name__=f.__name__ 
    return wrap


@app.route("/") 
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/ingreso",methods=["post"])
def ingreso():
    usuario=request.form["usuario"]
    password=request.form["password"]

    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND password=%s LIMIT 1",(usuario,password)) 
    usuario=cur.fetchone()  
    cur.close()

    if usuario:
        if usuario[3]==1: 
            session["usuario"]=usuario[1] 
            session["usuario_id"]=usuario[0]
            session["rol"]=usuario[5]
                
            cur=mysql.connection.cursor()
            cur.execute("UPDATE `usuarios` SET `ultlogin`=now() WHERE usuario_id=%s",(session["usuario_id"],)) 
            mysql.connection.commit()
            cur.close()
                
            return redirect(url_for("listado")) 
        else:
            flash("Tu cuenta esta desactivada","ERROR")
            return redirect(url_for("login"))
    else:
        flash("Credenciales incorrectas","ERROR") 
        return redirect(url_for("login"))

@app.route("/listado")
@requiere_login 
def listado():
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT tareas.*, DATE_FORMAT(tareas.fecha,'%d/%m/%Y %H:%i'), prioridades.nombre FROM tareas INNER JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE creada_por={usuario_id} AND estado=1 ORDER BY tarea_id DESC") 
    lista=cur.fetchall() 

    cur.execute("SELECT * FROM prioridades")
    listaprioridades=cur.fetchall()

    cur.close() 
    return render_template("principal.html",tareas=lista,prioridades=listaprioridades,usuario=session["usuario"],rol=session["rol"]) 

@app.route("/agregar",methods=["POST"]) 
@requiere_login
def agregar():
    texto=request.form["texto"] 
    prioridad=int(request.form["prioridad"]) 
    creada_por=session["usuario_id"]

    cur=mysql.connection.cursor()
    cur.execute("INSERT INTO `tareas`(`texto`,`prioridad`,`creada_por`) VALUES (%s,%s,%s)",(texto,prioridad,creada_por)) 
    mysql.connection.commit() 
    cur.close()

    return redirect(url_for("listado"))

@app.route("/borrar/<int:tarea_id>",methods=["GET"])
@requiere_login
def borrar(tarea_id=False):
    try:
        creada_por=verificar_id_tarea(tarea_id)
        if session["usuario_id"]==creada_por:
            cur=mysql.connection.cursor()
            cur.execute(f"UPDATE `tareas` SET estado=2 WHERE tarea_id={tarea_id}")
            mysql.connection.commit() 
            cur.close()

            flash("Borrado correctamente","HECHO")
            return redirect(url_for("listado"))
        else:
            flash("No se puede borrar esa tarea","ERROR")
            return redirect(url_for("listado"))
    except TypeError: #si el valor de tarea_id es un id inexistente, entra en la excepcion
        flash("No puede realizar esa accion","ERROR")
        return redirect(url_for("listado"))     

@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))

@app.route("/exportar_excel")
@requiere_login 
def exportar_excel():
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT tareas.tarea_id,tareas.texto, DATE_FORMAT(tareas.fecha,'%d/%m/%Y %H:%i'),tareas.estado, prioridades.nombre FROM tareas INNER JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE creada_por={usuario_id} ORDER BY tarea_id DESC") 
    lista=cur.fetchall() 

    df=pd.DataFrame(lista,columns=["ID","TEXTO","FECHA","ESTADO","PRIORIDAD"]) 

    output=io.BytesIO() 

    with pd.ExcelWriter(output,engine="openpyxl") as writer: 
        df.to_excel(writer,index=False,sheet_name="Tareas") 

    output.seek(0) 

    cur.close() 
    return send_file(output,download_name="tareas.xlsx",as_attachment=True) 

@app.route("/reporte")
@requiere_login 
def reporte():
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(tareas.tarea_id) AS total, prioridades.nombre FROM tareas RIGHT JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE creada_por={usuario_id} AND estado=1 GROUP BY prioridades.nombre ORDER BY prioridades.prioridad_id") 
    lista=cur.fetchall()
    cur.close()

    df=pd.DataFrame(lista,columns=["Total","Nombre"]) 

    plt.figure(figsize=(8,6)) 
    plt.bar(df["Nombre"],df["Total"],color=["red","turquoise","gray"]) 
    plt.xlabel("Prioridades") 
    plt.ylabel("Cantidad") 
    plt.title("Distribucion de tareas PENDIENTES") 

    img=io.BytesIO() 
    plt.savefig(img,format="png") 
    img.seek(0) 

    grafico=base64.b64encode(img.getvalue()).decode("utf-8")

    return render_template("reporte.html",grafico_img=grafico,usuario=session["usuario"],rol=session["rol"])

@app.route("/generar_qr/<int:tarea_id>",methods=["GET"])
@requiere_login 
def generar_qr(tarea_id=False):
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT tareas.*, DATE_FORMAT(tareas.fecha,'%d/%m/%Y %H:%i'), prioridades.nombre FROM tareas INNER JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE tarea_id={tarea_id} LIMIT 1") 
    tarea=cur.fetchone()
    cur.close()

    qr=qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, 
        box_size=8,
        border=4,
    )

    texto="TAREA:"+tarea[1]+"\n FECHA:"+tarea[6]+"\n PRIORIDAD:"+tarea[7] 
    qr.add_data(texto) 
    qr.make(fit=True)

    buf=qr.make_image(fill_color="blue",back_color="white") 

    img=io.BytesIO() 
    buf.save(img,format="png") 
    img.seek(0) 

    qr_img=base64.b64encode(img.getvalue()).decode("utf-8") 

    return render_template("qr.html",qr_img=qr_img,usuario=session["usuario"],rol=session["rol"])

@app.route("/nuevo_usuario")
def nuevo_usuario():
    return render_template("crear_usuario.html")

@app.route("/crear_usuario",methods=["post"])
def crear_usuario():
    usuario=request.form["usuario"]
    password1=request.form["password"]
    password2=request.form["repetir_pass"]

    if not password1==password2:
        flash("Repita la contraseña correctamente","ERROR")
        return redirect(url_for("nuevo_usuario"))
    else:  
        cur=mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s LIMIT 1",(usuario,)) 
        user=cur.fetchone()
        cur.close()

        if user:
            flash("El nombre de usuario no esta disponible","ERROR")
            return redirect(url_for("nuevo_usuario")) 
        else:
            cur=mysql.connection.cursor()
            cur.execute("INSERT INTO `usuarios`(`usuario`,`password`) VALUES (%s,%s)",(usuario,password1)) 
            mysql.connection.commit() 
            cur.close()
            
            flash("Usuario creado correctamente","APROBADO") 
            return redirect(url_for("login")) 

@app.route("/lista_usuarios")
@requiere_login
@requiere_admin
def lista_usuarios():
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT usuarios.usuario_id, usuarios.usuario, usuarios.estado, usuarios.ultlogin, roles.rol FROM usuarios INNER JOIN roles ON usuarios.rol_id=roles.rol_id WHERE usuarios.estado=1 OR usuarios.estado=2 ORDER BY usuarios.usuario_id ASC") 
    lista=cur.fetchall() 

    cur.close() 
    return render_template("lista_usuarios.html",usuarios=lista,usuario=session["usuario"],rol=session["rol"])

@app.route("/terminada/<int:tarea_id>",methods=["GET"]) 
@requiere_login
def terminada(tarea_id=False):
    try:
        creada_por=verificar_id_tarea(tarea_id) 
        if session["usuario_id"]==creada_por:
            cur=mysql.connection.cursor()
            cur.execute(f"UPDATE `tareas` SET estado=3 WHERE tarea_id={tarea_id}")
            mysql.connection.commit()
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("listado"))
        else:
            flash("No se puede realizar esa accion","ERROR")
            return redirect(url_for("listado"))
    except TypeError: #si el valor de tarea_id es un id inexistente, entra en la excepcion
        flash("No puede realizar esa accion","ERROR")
        return redirect(url_for("listado"))     

@app.route("/reporte_terminadas")
@requiere_login 
def reporte_terminadas():
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(tareas.tarea_id) AS total, prioridades.nombre FROM tareas RIGHT JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE creada_por={usuario_id} AND estado=3 GROUP BY prioridades.nombre ORDER BY prioridades.prioridad_id") 
    lista=cur.fetchall()
    cur.close()

    df=pd.DataFrame(lista,columns=["Total","Nombre"]) 

    plt.figure(figsize=(8,6)) 
    plt.bar(df["Nombre"],df["Total"],color=["red","turquoise","gray"]) 
    plt.xlabel("Prioridades")
    plt.ylabel("Cantidad") 
    plt.title("Distribucion de tareas TERMINADAS") 

    img=io.BytesIO() 
    plt.savefig(img,format="png") 
    img.seek(0) 

    grafico=base64.b64encode(img.getvalue()).decode("utf-8") 
    
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT tareas.*, DATE_FORMAT(tareas.fecha,'%d/%m/%Y %H:%i'), prioridades.nombre FROM tareas INNER JOIN prioridades ON tareas.prioridad=prioridades.prioridad_id WHERE creada_por={usuario_id} AND estado=3 ORDER BY tarea_id DESC") 
    listado=cur.fetchall()
    cur.close()

    return render_template("reporte_terminadas.html",grafico_img=grafico,usuario=session["usuario"],rol=session["rol"],terminadas=listado)

@app.route("/restablecer_pendiente/<int:tarea_id>",methods=["GET"]) 
@requiere_login
def restablecer_pendiente(tarea_id=False):
    creada_por=verificar_id_tarea(tarea_id)
    if session["usuario_id"]==creada_por:
        cur=mysql.connection.cursor()
        cur.execute(f"UPDATE `tareas` SET estado=1 WHERE tarea_id={tarea_id}")
        mysql.connection.commit() 
        cur.close()

        flash("Restablecido correctamente","HECHO")
        return redirect(url_for("reporte_terminadas"))
    else:
        flash("No se puede realizar esa accion","ERROR")
        return redirect(url_for("reporte_terminadas"))

@app.route("/grafico_torta")
@requiere_login 
def grafico_torta():
    usuario_id=int(session["usuario_id"])
    cur=mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(tareas.tarea_id) AS total FROM tareas WHERE creada_por={usuario_id} AND estado=1") 
    pendientes=cur.fetchone()[0] 
    
    cur.execute(f"SELECT COUNT(tareas.tarea_id) AS total FROM tareas WHERE creada_por={usuario_id} AND estado=3") 
    terminadas=cur.fetchone()[0]
    cur.close()

    if pendientes or terminadas:
        labels=["Pendientes","Terminadas"]
        sizes=[pendientes,terminadas]
        colors=["red","lightgreen"]

        plt.figure(figsize=(8,6))
        plt.pie(sizes,labels=labels,colors=colors,autopct=lambda p: f'{int(p * sum(sizes) / 100)} ({p:.1f}%)') 
        plt.title("Distribucion de tareas pendientes y terminadas")

        img=io.BytesIO() 
        plt.savefig(img,format="png")
        img.seek(0) 

        grafico=base64.b64encode(img.getvalue()).decode("utf-8")
    
    else:
        grafico=None

    return render_template("grafico_torta.html",grafico_img=grafico,usuario=session["usuario"],rol=session["rol"])

@app.route("/dar_admin/<int:usuario_id>",methods=["GET"]) 
@requiere_login
@requiere_creador
def dar_admin(usuario_id=False):
    try:
        cur=mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s LIMIT 1",(usuario_id,))
        user=cur.fetchone()
        cur.close()
        rol=user[5] #rol del usuario seleccionado para dar admin
        
        if not rol==3: # rol 3 = creador
            cur=mysql.connection.cursor()
            cur.execute(f"UPDATE `usuarios` SET rol_id=1 WHERE usuario_id={usuario_id}")
            mysql.connection.commit() 
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("lista_usuarios"))
        else:
            flash("No puede realizar esa accion","ERROR")
            return redirect(url_for("lista_usuarios"))
    except TypeError: #si el valor de usuario_id es un id inexistente, entra en la excepcion
        flash("No puede realizar esa accion","ERROR")
        return redirect(url_for("lista_usuarios"))        

@app.route("/sacar_admin/<int:usuario_id>",methods=["GET"]) 
@requiere_login
@requiere_creador
def sacar_admin(usuario_id=False):
    try:
        cur=mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s LIMIT 1",(usuario_id,))
        user=cur.fetchone()
        cur.close()
        rol=user[5] #rol del usuario seleccionado para sacar admin
        
        if not rol==3: # rol 3 = creador
            cur=mysql.connection.cursor()
            cur.execute(f"UPDATE `usuarios` SET rol_id=2 WHERE usuario_id={usuario_id}")
            mysql.connection.commit() 
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("lista_usuarios"))
        else:
            flash("No puede realizar esa accion","ERROR")
            return redirect(url_for("lista_usuarios"))
    except TypeError: #si el valor de usuario_id es un id inexistente, entra en la excepcion
        flash("No puede realizar esa accion","ERROR")
        return redirect(url_for("lista_usuarios"))        

@app.route("/dar_de_baja/<int:usuario_id>",methods=["GET"]) 
@requiere_login
@requiere_admin
def dar_de_baja(usuario_id=False):
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s LIMIT 1",(usuario_id,))
    user=cur.fetchone()
    cur.close()
    rol=user[5] #rol del usuario seleccionado para dar de baja
    
    if session["rol"]==3: # rol 3 = creador
        if not rol==3: 
            cur=mysql.connection.cursor()
            cur.execute("UPDATE usuarios SET estado=%s WHERE usuario_id=%s", (2, usuario_id))
            mysql.connection.commit() 
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("lista_usuarios"))
        else:
            flash("No puede realizar esa accion","ERROR")
            return redirect(url_for("lista_usuarios"))
    else: 
        if rol==2: # rol 2 = usuario
            cur=mysql.connection.cursor()
            cur.execute("UPDATE usuarios SET estado=%s WHERE usuario_id=%s", (2, usuario_id))
            mysql.connection.commit() 
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("lista_usuarios"))
        else:
            flash("No puede realizar esa accion","ERROR")
            return redirect(url_for("lista_usuarios"))

@app.route("/dar_de_alta/<int:usuario_id>",methods=["GET"])
@requiere_login
@requiere_admin
def dar_de_alta(usuario_id=False):
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s LIMIT 1",(usuario_id,))
    user=cur.fetchone()
    cur.close()
    rol=user[5] #rol del usuario seleccionado para dar de alta
    
    if session["rol"]==3: #rol 3 = creador
        cur=mysql.connection.cursor()
        cur.execute(f"UPDATE `usuarios` SET estado=1 WHERE usuario_id={usuario_id}")
        mysql.connection.commit() 
        cur.close()

        flash("Cambio realizado correctamente","HECHO")
        return redirect(url_for("lista_usuarios"))
        
    else: 
        if rol==2: # rol 2 = usuario
            cur=mysql.connection.cursor()
            cur.execute(f"UPDATE `usuarios` SET estado=1 WHERE usuario_id={usuario_id}")
            mysql.connection.commit() 
            cur.close()

            flash("Cambio realizado correctamente","HECHO")
            return redirect(url_for("lista_usuarios"))
        else:
            flash("No puede realizar esa accion","ERROR")
            return redirect(url_for("lista_usuarios"))
             
@app.route("/nueva_pass")
@requiere_login
def nueva_pass():
    return render_template("cambiar_pass.html",usuario=session["usuario"],rol=session["rol"])

@app.route("/cambiar_pass",methods=["post"])
@requiere_login
def cambiar_pass():
    usuario=session["usuario_id"]
    pass_actual=request.form["pass_actual"]
    nueva_pass=request.form["pass_nueva"]
    nueva_pass2=request.form["repetir_pass"]

    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s AND password=%s LIMIT 1",(usuario,pass_actual)) 
    user=cur.fetchone()
    cur.close()

    if user:
        if nueva_pass==nueva_pass2:
            cur=mysql.connection.cursor()
            cur.execute("UPDATE usuarios SET password=%s WHERE usuario_id=%s", (nueva_pass, usuario))
            mysql.connection.commit()
            cur.close()
            
            flash("Contraseña actualizada correctamente","APROBADO") 
            return redirect(url_for("nueva_pass")) 
        else:
            flash("Repita la contraseña correctamente","ERROR")
            return redirect(url_for("nueva_pass"))
    else:
        flash("Contraseña incorrecta","ERROR")
        return redirect(url_for("nueva_pass"))


if __name__=="__main__":
    app.run(debug=True)
