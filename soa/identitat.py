import settings
import re
import requests


class GestioIdentitat:

    def __init__(self):
        self.url = "https://identitatdigital.upc.edu/gcontrol/rest"
        self.token = self.get_token()
        self.identitat_local = GestioIdentitatLocal()

    def get_token(self):
        try:
            resposta = requests.post(
                self.url+"/acls/processos",
                data={'idProces': settings.get("identitat_digital_apikey")})
            token = resposta.json()['tokenAcl']
            return token
        except Exception:
            return None

    def canonicalitzar_mail(self, mail):
        if mail is None:
            return None
        mail_canonic = mail.lower()
        mail_canonic = mail_canonic.replace(".upc.es", ".upc.edu")
        mail_canonic = mail_canonic.replace("@lsi", "@cs")
        return mail_canonic

    def obtenir_uid(self, mail):
        mail_canonic = self.canonicalitzar_mail(mail)
        uid = self.identitat_local.obtenir_uid_de_llista(mail_canonic)
        if uid is None:
            uid = self.obtenir_uid_remot(mail_canonic)

        if uid is None:
            uid = self.identitat_local.obtenir_uid_de_patrons(mail_canonic)

        return uid

    def obtenir_uid_remot(self, mail):
        try:
            # Pot ser que un usuari d'un departament no tingui a identitat
            # digital un mail del tipus @upc.edu, aixi que primer comprovem
            # si la part esquerra del mail correspon a un usuari UPC real
            if "@upc.edu" in mail:
                cn = mail.split("@")[0]
                try:
                    cn = mail.split("@")[0]
                    persona = requests.get(
                        self.url+"/externs/persones/"+cn+"/cn",
                        headers={'TOKEN': self.token}).json()
                    return persona['commonName']
                except Exception:
                    None

            # Si no hi ha correspondencia directa amb un usuari UPC
            # busquem a partir del mail qui pot ser
            cns = requests.get(self.url+"/externs/identitats/cn?email=" + mail,
                               headers={'TOKEN': self.token}).json()
            if len(cns) == 1:
                # Quan tenim un resultat, es aquest
                return cns[0]
            else:
                # Si tenim mes d'un, busquem el que te el mail que busquem
                # com a preferent o be retornem el primer
                for cn in cns:
                    try:
                        persona = requests.get(
                            self.url+"/externs/persones/"+cn+"/cn",
                            headers={'TOKEN': self.token}).json()
                        email_preferent = persona['emailPreferent']
                        if (self.canonicalitzar_mail(email_preferent) == mail):
                            return persona['commonName']
                    except Exception:
                        None
                return None
        except Exception:
            return None


class GestioIdentitatLocal:

    def __init__(self):
        self.mails_addicionals = settings.get("mails_addicionals")
        self.patrons_mails_addicionals \
            = settings.get("patrons_mail_addicionals")

    def obtenir_uid_local(self, mail):
        uid = self.obtenir_uid_de_llista(mail)
        if uid is None:
            uid = self.obtenir_uid_de_patrons(mail)

        return uid

    def obtenir_uid_de_llista(self, mail):
        try:
            return self.mails_addicionals[mail]
        except Exception:
            return None

    def obtenir_uid_de_patrons(self, mail):
        try:
            for k, v in self.patrons_mails_addicionals.iteritems():
                patro = re.compile(k)
                m = patro.match(mail)
                if m:
                    try:
                        return v % m.group(1)
                    except Exception:
                        return v

            return None
        except Exception:
            return None
