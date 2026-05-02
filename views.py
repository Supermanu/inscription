# This file is part of HappySchool.
#
# HappySchool is the legal property of its developers, whose names
# can be found in the AUTHORS file distributed with this source
# distribution.
#
# HappySchool is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HappySchool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with HappySchool.  If not, see <http://www.gnu.org/licenses/>.

import json
import xlwt
from unidecode import unidecode
import requests
from collections import Counter

from io import BytesIO

from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from django_filters import rest_framework as filters

from django_weasyprint import WeasyTemplateView

from rest_framework.permissions import (
    IsAuthenticated,
    DjangoModelPermissions,
    BasePermission,
)
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.views import (
    BaseFilters,
    BaseModelViewSet,
    get_app_settings,
    PageNumberSizePagination,
)
from core.utilities import get_menu


from .models import InscriptionSettingsModel, InscriptionModel
from .serializers import InscriptionSettingsSerializer, InscriptionSerializer
from datetime import datetime

def get_menu_entry(active_app, request):
    if not request.user.has_perm("inscription.view_inscriptionsettingsmodel"):
        return {}
    return {
        "app": "inscription",
        "display": "Inscriptions",
        "url": "/inscription/",
        "active": active_app == "inscription",
    }


def get_settings():
    return get_app_settings(InscriptionSettingsModel)


class InscriptionView(
    LoginRequiredMixin,
    # PermissionRequiredMixin,
    TemplateView,
):
    template_name = "inscription/inscription.html"
    permission_required = "inscription.view_inscriptionsettingsmodel"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["menu"] = json.dumps(get_menu(self.request, "inscription"))
        context["filters"] = json.dumps([])
        context["settings"] = json.dumps(
            (InscriptionSettingsSerializer(get_settings()).data)
        )
        context["can_validate"] = json.dumps(
            self.request.user.has_perm("inscription.add_inscriptionmodel")
        )
        context["remote_url"] = json.dumps(settings.SUBSCRIBE_URL)

        return context


class InscriptionFilter(filters.FilterSet):
    subscription__study_year = filters.CharFilter(method="by_study_year")
    subscription__study_option__id = filters.CharFilter(method="by_study_option")

    class Meta:
        model = InscriptionModel
        fields = ["matricule", "scholar_year", "is_validated"]

    def by_study_year(self, queryset, field_name, value):
        if value:
            return queryset.filter(subscription__study_year=value)
        else:
            return queryset

    def by_study_option(self, queryset, field_name, value):
        if value and value.isdigit():
            return queryset.filter(subscription__study_option__id=int(value))
        else:
            return queryset


class InscriptionViewSet(ModelViewSet):
    queryset = InscriptionModel.objects.all()
    serializer_class = InscriptionSerializer
    permission_classes = (
        IsAuthenticated,
        DjangoModelPermissions,
    )
    pagination_class = PageNumberSizePagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = InscriptionFilter

    # Génération d'un matricule unique pour chaque nouvelle inscription : dernier généré dans la DB + 1
    def _generate_matricule(self, serializer):
        # print("=== [InscriptionViewSet._generate_matricule]")
        prefix = serializer.validated_data["scholar_year"][6:]
        last_subscription = (
            InscriptionModel.objects.filter(
                scholar_year=serializer.validated_data["scholar_year"],
                is_validated=True,
            )
            .order_by("-matricule")
            .first()
        )

        suffix = int(last_subscription.matricule[-3:]) + 1 if last_subscription else 1
        return f"{prefix}{str(suffix).zfill(3)}"

    def perform_create(self, serializer):
        if (
            serializer.validated_data["is_validated"]
            and serializer.validated_data["scholar_year"]
        ):
            serializer.save(matricule=self._generate_matricule(serializer))
        else:
            serializer.save(matricule="undefined")

    def perform_update(self, serializer):
        # print("=== [InscriptionViewSet.perform_update]")
        if (
            serializer.instance.matricule == "undefined"
            and serializer.validated_data["is_validated"]
        ):
            serializer.save(matricule=self._generate_matricule(serializer))
        else:
            serializer.save()


class HasInscriptionPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("inscription.view_inscriptionsettingsmodel")


class SubscriptionAPI(APIView):
    permission_classes = [
        HasInscriptionPermission,
    ]
    host = settings.SUBSCRIBE_URL

    def _get_inscription_model(self, uuid):
        try:
            return InscriptionSerializer(InscriptionModel.objects.get(uuid=uuid)).data
        except ObjectDoesNotExist:
            return None

    # Récupère la liste des inscriptions dans le backend et les retourne dans l'objet subscriptions
    def get(self, request, *args, **kwargs):
        # print("=== [SubscriptionAPI.get]")

        page = kwargs.get("page")
        is_complete = kwargs.get("is_complete")
        scholar_year = kwargs.get("scholar_year")
        pending = kwargs.get("pending") == "true"
        search = kwargs.get("search", "")

        # Si 'pending' : va chercher les info dans InscriptionModel et retourne directement 'subscriptions'
        if pending:
            pending_sub = InscriptionModel.objects.filter(
                pending=True, scholar_year=scholar_year
            )
            subscriptions = [
                {
                    "uuid": sub["uuid"],
                    "student": f"{sub.subscription['student']['last_name']} {sub.subscription['student']['first_name']}",
                    "year": sub.subscription["study_year"],
                    "option": sub.subscription["study_option"],
                    "date": (
                        sub.subscription["datetime_completion"][0:10]
                        if sub.subscription["datetime_completion"]
                        else sub.subscription["datetime_update"][0:10]
                    ),
                    "father": (
                        sub.subscription["father"]["last_name"]
                        if sub.subscription["father"]
                        else ""
                    ),
                    "mother": (
                        sub.subscription["mother"]["last_name"]
                        if sub.subscription["mother"]
                        else ""
                    ),
                    "other": (
                        sub.subscription["other_responsible"]["last_name"]
                        if sub.subscription["other_responsible"]
                        else ""
                    ),
                    "is_completed": sub.subscription["is_completed"],
                    # "validation": resp[1].data.results.find(ins => ins.uuid === sub.uuid),
                    "dump": sub.subscription,
                    "validation": InscriptionSerializer(sub).data,
                }
                for sub in pending_sub
            ]
            return Response({"results": subscriptions, "next": None})

        # Si pas 'pending' : demande les info au service d'inscription et retourne 'subscriptions'
        big_page = "&page_size=400" if is_complete == "false" else ""
        r = requests.get(
            f"{self.host}/subscribe/api/subscriptionremote/?is_completed={is_complete}&search={search}&scholar_year={scholar_year}&page={page}&order{big_page}",
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
        )

        data = r.json()
        subscriptions = [
            {
                "uuid": sub["uuid"],
                "student": f"{sub['student']['last_name']} {sub['student']['first_name']}",
                "year": sub["study_year"],
                "option": sub["study_option"],
                "date": (
                    sub["datetime_completion"][0:10]
                    if sub["datetime_completion"]
                    else sub["datetime_update"][0:10]
                ),
                "father": sub["father"]["last_name"] if sub["father"] else "",
                "mother": sub["mother"]["last_name"] if sub["mother"] else "",
                "other": (
                    sub["other_responsible"]["last_name"]
                    if sub["other_responsible"]
                    else ""
                ),
                "is_completed": sub["is_completed"],
                "dump": sub,
                "validation": self._get_inscription_model(sub["uuid"]),
            }
            for sub in data["results"]
            if sub["student"] and sub["student"]["last_name"]
        ]
        # if pending:
        # subscriptions = [sub for sub in subscriptions if sub["validation"] and sub["validation"]["pending"]]
        return Response({"results": subscriptions, "next": data["next"]})


class ValidationAPI(APIView):
    permission_classes = [
        HasInscriptionPermission,
    ]
    host = settings.SUBSCRIBE_URL

    def post(self, request, *args, **kwargs):
        uuid = request.data["uuid"]
        if not uuid:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        requests.patch(
            f"{self.host}/subscribe/api/subscriptionremote/{uuid}/",
            {"is_completed": True},
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
        )
        return Response({"status": "done"})


class StatsAPI(APIView):
    permission_classes = [
        HasInscriptionPermission,
    ]
    host = settings.SUBSCRIBE_URL

    def get(self, request, *args, **kwargs):
        scholar_year = kwargs.get("scholar_year")
        inscriptions = [
            f'{insc.subscription["study_option"]["id"]}_{insc.subscription["study_year"]}'
            for insc in InscriptionModel.objects.filter(
                scholar_year=scholar_year, is_validated=True
            )
        ]

        insc_count = Counter(inscriptions)

        r = requests.get(
            f"{self.host}/resubscribe/api/resubscriberemote/",
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
        )

        data = r.json()

        resubscription = [
            f'{resub["next_option"]}_{resub["next_year"]}'
            for resub in data["results"]
            if resub["next_option"]
        ]

        resub_count = Counter(resubscription)

        return Response(
            {"sub_count": dict(insc_count), "resub_count": dict(resub_count)}
        )


# Génération du fichier .pdf
class ExportPDFInscription(WeasyTemplateView):
    template_name = "inscription/pdflist.html"
    host = settings.SUBSCRIBE_URL

    def get_context_data(self, **kwargs) -> dict:
        # print("=== [ExportPDFInscription.get_context_data]")
        context = super().get_context_data(**kwargs)
        scholar_year = kwargs.get("scholar_year")
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")
        not_validated_only = kwargs.get("not_validated_only", "false") == "true"

        r = requests.get(
            f"{self.host}/subscribe/api/subscriptionremote/?is_completed=True&scholar_year={scholar_year}&page_size=2000&date_from={date_from}&date_to={date_to}",
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
        )

        family = ["father", "mother", "student"]
        results = r.json()["results"]
        if not_validated_only:
            results = [
                sub
                for sub in results
                if InscriptionModel.objects.filter(
                    uuid=sub["uuid"], is_validated=False
                ).exists()
                or not InscriptionModel.objects.filter(uuid=sub["uuid"]).exists()
            ]

        context["inscriptions"] = [
            {
                **sub,
                "resp": (
                    sub[sub["responsible"]]
                    if sub["responsible"] in family
                    else sub["other_responsible"]
                ),
            }
            for sub in results
        ]
        context["date_from"] = date_from
        context["date_to"] = date_to
        return context


class RemoteServerAPI(APIView):
    """Redirect allowed requests to remote server."""

    http_method_names = ["get", "delete"]
    permission_classes = [
        HasInscriptionPermission,
    ]
    host = settings.SUBSCRIBE_URL
    get_allowed_path = [
        "resubscribe/api/resubscriberemote/",
        "subscribe/api/option/",
        "subscribe/api/option_by_year/",
    ]

    delete_allowed_path = "subscribe/api/subscriptionremote/"

    def delete(self, request, *args, **kwargs):
        remote_path = kwargs.get("path", None)

        if not remote_path or self.delete_allowed_path not in remote_path:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        remote_url = f"{self.host}/{remote_path}"

        r = requests.delete(
            remote_url,
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
        )
        try:
            r.raise_for_status()
        except requests.HTTPError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_202_ACCEPTED)

    def get(self, request, *args, **kwargs):
        # print("=== [RemoteServerAPI.get]")
        remote_path = kwargs.get("path", None)
        print(f"Remote path {remote_path}")
        if not remote_path or remote_path not in self.get_allowed_path:
            print("not allowed")
            return Response(status=status.HTTP_404_NOT_FOUND)

        remote_url = f"{self.host}/{remote_path}"
        print(f"Remote url {remote_url}")

        r = requests.get(
            remote_url,
            headers={"Authorization": f"Token {settings.SUBSCRIBE_TOKEN}"},
            params=request.GET,
        )
        try:
            r.raise_for_status()
        except requests.HTTPError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(data=r.json())


class ExportInscriptionViewclass(View):
    def _date_to_proeco(self, date):
        return f"{date[8:10]}{date[5:7]}{date[:4]}"

    def _country_to_proeco(self, country):
        if (
            country.lower() == "belgique"
            or country.lower() == "belge"
            or country.lower() == "be"
        ):
            return "BE"
        return country

    def _get_matinfo(self, register_id):
        return None
        # from libreschoolfdb import reader

        # fdb_server = settings.SYNC_FDB_SERVER[0]["server"]
        # return reader.get_matricule_from_register_id(register_id, fdb_server)

    # Génération du fichier .xls
    def get(self, request, *args, **kwargs):
        # print("=== [ExportInscriptionViewclass.get]")
        uuid = kwargs["subscription"]
        try:
            subscription_model = InscriptionModel.objects.get(uuid=uuid)
            subscription = subscription_model.subscription
        except ObjectDoesNotExist:
            # Class not found
            return HttpResponse(status_code=404)

        # print("*** subscription : ", subscription)

        # Création d'un fichier .xls avec une feuille nommée 'data'
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet("data")
        # workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # worksheet = workbook.add_worksheet()

        # Données générales
        # - Titre colonnes
        columns = [
            "Date debut",
            "Ecole",
            "AnSco",
            "An",
            "Fo",
            "Fi",
            "Statut",
            "Numero de registre",
            "Nom",
            "Prenom",
            "Nationalite",
            "datenaiss",
            "Majeur ou Mineur",
            "Pays de naissance",
            "Lieu de naissance",
            "Numero carte identite",
            "Numero national",
            "Date Validité",
            "Date entree",
            "Date 1ere entree",
            "email",
            "gsm",
            "adresse",
            "code postal",
            "Commune",
            "localite",
            "Pays",
            "Integration",
            "CPU",
            "Sante",
            "logopede",
            "sexe",
            "matricule",
            "classe",
            "orientation",
            "religion",
            "langue 1",
            "Envoi",                # deprecated
            "Correspondance",       # deprecated
            "Papier/sms/mail",
            "Zone",
            "Besoin de FLE",
        ]

        # Father
        # - Titre colonnes
        columns += [
            "NomPere",
            "PrenomPere",
            "NationalitePere",
            "emailPere",
            "Pere tel maison",
            "Pere tel travail",
            "Pere gsm",
            "Pere adresse",
            "Pere code postal",
            "Pere commune",
            "Pere localite",
            "Pere pays",
            "Titre Pere",
            "Titre nom prenom Pere",
            "Sexe Pere",
            "Zone Pere",
        ]
        # - Préparation des données dans 'data_father'
        street_father = ""
        if subscription["father"]:
            street_father = f'{subscription["father"]["address"]["street"]}, {subscription["father"]["address"]["street_number"]}'
            if subscription["father"]["address"]["box_number"]:
                street_father += (
                    f" boîte {subscription['father']['address']['box_number']}"
                )
        data_father = [
            subscription["father"]["last_name"] if subscription["father"] else "",
            subscription["father"]["first_name"] if subscription["father"] else "",
            (
                self._country_to_proeco(subscription["father"]["nationality"])
                if subscription["father"]
                else ""
            ),
            subscription["father"]["email"] if subscription["father"] else "",
            subscription["father"]["phone_home"] if subscription["father"] else "",
            subscription["father"]["phone_work"] if subscription["father"] else "",
            subscription["father"]["mobile_phone"] if subscription["father"] else "",
            street_father,
            (
                subscription["father"]["address"]["postal_code"]
                if subscription["father"]
                else ""
            ),
            (
                subscription["father"]["address"]["municipality"]
                if subscription["father"]
                else ""
            ),
            (
                subscription["father"]["address"]["locality"]
                if subscription["father"]
                else ""
            ),
            "BE",
            "Monsieur" if subscription["father"] else "",
            (
                f'Monsieur {subscription["father"]["last_name"]} {subscription["father"]["first_name"]}'
                if subscription["father"]
                else ""
            ),
            "M" if subscription["father"] else "",
            "B",
        ]

        # Mother
        # - Titre colonnes
        columns += [
            "NomMere",
            "PrenomMere",
            "NationaliteMere",
            "emailMere",
            "Mere tel maison",
            "Mere tel travail",
            "Mere gsm",
            "Mere adresse",
            "Mere code postal",
            "Mere commune",
            "Mere localite",
            "Mere Pays",
            "Titre Mere",
            "Titre nom prenom Mere",
            "Sexe Mere",
            "Zone Mere",
        ]

        # - Préparation des données dans 'data_mother'
        street_mother = ""
        if subscription["mother"]:
            street_mother = f'{subscription["mother"]["address"]["street"]}, {subscription["mother"]["address"]["street_number"]}'
            if subscription["mother"]["address"]["box_number"]:
                street_mother += (
                    f" boîte {subscription['mother']['address']['box_number']}"
                )

        data_mother = [
            subscription["mother"]["last_name"] if subscription["mother"] else "",
            subscription["mother"]["first_name"] if subscription["mother"] else "",
            (
                self._country_to_proeco(subscription["mother"]["nationality"])
                if subscription["mother"]
                else ""
            ),
            subscription["mother"]["email"] if subscription["mother"] else "",
            subscription["mother"]["phone_home"] if subscription["mother"] else "",
            subscription["mother"]["phone_work"] if subscription["mother"] else "",
            subscription["mother"]["mobile_phone"] if subscription["mother"] else "",
            street_mother,
            (
                subscription["mother"]["address"]["postal_code"]
                if subscription["mother"]
                else ""
            ),
            (
                subscription["mother"]["address"]["municipality"]
                if subscription["mother"]
                else ""
            ),
            (
                subscription["mother"]["address"]["locality"]
                if subscription["mother"]
                else ""
            ),
            "BE",
            "Madame" if subscription["mother"] else "",
            (
                f'Madame {subscription["mother"]["last_name"]} { subscription["mother"]["first_name"]}'
                if subscription["mother"]
                else ""
            ),
            "F" if subscription["mother"] else "",
            "B",
        ]

        # Responsible
        # - Titre colonnes
        columns += [
            "NomResp",
            "PrenomResp",
            "NationaliteResp",
            "emailResp",
            "Resp tel maison",
            "Resp tel travail",
            "Resp gsm",
            "Resp adresse",
            "Resp code postal",
            "Resp commune",
            "Resp localite",
            "Resp pays",
            "Titre Resp",
            "Titre nom prenom Resp",
            "Sexe Resp",
            "Zone Resp",
            "statut Resp",
            "Envoi Resp",
            "Correspondance Resp",
        ]

        # - Préparation des données dans 'data_resp'
        if subscription["responsible"] == "father":
            resp_nom_prenom = f'{subscription["father"]["last_name"]} {subscription["father"]["first_name"]}'
            data_resp = data_father.copy()
            data_resp[-4] = "Monsieur" if not subscription["mother"] else "M. et Mme"
            data_resp[-3] = (
                f"Monsieur {resp_nom_prenom}"
                if not subscription["mother"]
                else f"M. et Mme {resp_nom_prenom}"
            )
            data_resp.append("1")
            data_resp.append("SMS")
            data_resp.append("+")
        elif subscription["responsible"] == "mother":
            resp_nom_prenom = f'{subscription["mother"]["last_name"]} { subscription["mother"]["first_name"]}'
            data_resp = data_mother.copy()
            data_resp[-4] = "Madame" if not subscription["mother"] else "M. et Mme"
            data_resp[-3] = (
                f"Madame {resp_nom_prenom}"
                if not subscription["mother"]
                else f"M. et Mme {resp_nom_prenom}"
            )
            data_resp.append("2")
            data_resp.append("SMS")
            data_resp.append("+")
        else:
            street_resp = ""
            if subscription["other_responsible"]:
                street_resp = f'{subscription["other_responsible"]["address"]["street"]}, {subscription["other_responsible"]["address"]["street_number"]}'
                if subscription["other_responsible"]["address"]["box_number"]:
                    street_resp += f" boîte {subscription['other_responsible']['address']['box_number']}"
            data_resp = [
                (
                    subscription["other_responsible"]["last_name"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["first_name"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    self._country_to_proeco(
                        subscription["other_responsible"]["nationality"]
                    )
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["email"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["phone_home"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["phone_work"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["mobile_phone"]
                    if subscription["other_responsible"]
                    else ""
                ),
                street_resp,
                (
                    subscription["other_responsible"]["address"]["postal_code"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["address"]["municipality"]
                    if subscription["other_responsible"]
                    else ""
                ),
                (
                    subscription["other_responsible"]["address"]["locality"]
                    if subscription["other_responsible"]
                    else ""
                ),
                "BE",
                "",  # Titre resp
                "",  # Titre nom prenom resp
                "",  # Sexe resp
                "B",  # Zone resp
                "",  # Statut
                "SMS",
                "+",
            ]


        # Free address
        # - Titre colonnes
        columns += [
            "NomRespFree",
            "PrenomRespFree",
            "NationaliteRespFree",
            "emailRespFree",
            "RespFree tel maison",
            "RespFree tel travail",
            "RespFree gsm",
            "RespFree adresse",
            "RespFree code postal",
            "Resp Freecommune",
            "Resp Freelocalite",
            "RespFree pays",
            "Titre RespFree",
            "Titre nom prenom RespFree",
            "Sexe RespFree",
            "Zone RespFree",
            "statut RespFree",
            "Envoi RespFree",
            "Correspondance RespFree",
        ]
        # - Préparation des données dans 'data_free_address'
        data_free_address = data_resp.copy()


        # Last school
        # - Titre colonnes
        columns += [
            "",
        ]
        # - Préparation des données dans 'data_free_address'
        data_last_school = []


        # Préparation des données générales dans les différentes colonnes correspondantes
        an = subscription["study_year"].upper()
        form = (
            subscription["study_option"]["form"]["form"][0].upper()
            if subscription["study_option"]["form"]
            else ""
        )
        channel = (
            subscription["study_option"]["channel"]["channel"][0]
            .upper()
            .replace("-", "")
            if subscription["study_option"]["channel"]
            else ""
        )

        if form == "T" and channel == "Q" and int(an[0]) >= 4:
            form = "E"
        if form == "P" and int(an[0]) > 3 and int(an[0]) < 7:
            form = "L"
        if (
            subscription["study_option"]["form"]
            and "type B" in subscription["study_option"]["form"]["form"]
        ):
            an += "B"       # On a que des options de type B en 7e, pas de B ajouté pour les autres années

        default_classe = (
            subscription["study_option"]["classe"]
            if "classe" in subscription["study_option"]
            else ""
        )
        orientation = (
            subscription["study_option"]["orientation"]
            if "orientation" in subscription["study_option"]
            else ""
        )
        if orientation == "EM":
            orientation = "ELMEC"
        if orientation == "BOIS":
            orientation = "MEN"

        # anfofi = f"{subscription['study_year']} {form}{channel}"

        student_id = self._get_matinfo(f"022{str(subscription_model.id).zfill(3)}")

        street_student = f'{subscription["student"]["address"]["street"]}, {subscription["student"]["address"]["street_number"]}'
        if subscription["student"]["address"]["box_number"]:
            street_student += (
                f" boîte {subscription['student']['address']['box_number']}"
            )

        start_date = f"2408{subscription_model.scholar_year[:4]}"
        datenaiss = subscription["student_info"]["birth_date"]

        parsed_rentree = datetime.strptime(str(start_date), "%d%m%Y").date()
        parsed_naissce = datetime.strptime(str(datenaiss), "%Y-%m-%d").date()
        age = parsed_rentree.year - parsed_naissce.year
        if (parsed_rentree.month, parsed_rentree.day) < (parsed_naissce.month, parsed_naissce.day):
            age -= 1
        majormin = "+" if age >= 18 else "-"

        # Création de l'objet contenant toutes les données de l'inscription, colonne après colonne
        data = (
            [
                start_date,         # Date debut -> = jour de la rentrée scolaire
                1,                  # Ecole -> toujours '1' (= centre scolaire Eperonniers Mercelis CEFA dans PROECO)
                subscription_model.scholar_year.replace("-", "/"),  # Année scolaire
                an,                 # An -> l'année ou l'élève s'incrit (1C, 2C, 3, 4, 5, 6, 7B)
                form,               # Fo = La forme d'enseignement (P, T, E, L, B, S)               # TODO : quid inscriptions en 4C ou 6S ?
                channel,            # Fi = La filière (Q, T, P)
                "",                 # Statut ?
                subscription_model.matricule,
                subscription["student"]["last_name"],                                       # Nom
                subscription["student"]["first_name"],                                      # Prenom
                self._country_to_proeco(subscription["student"]["nationality"]),            # Nationalite
                self._date_to_proeco(datenaiss),                                            # datenaiss
                majormin,                                                                   # Majeur ou Mineur, à la date de la rentrée
                subscription["student_info"]["birth_country_obj"]["acronym"],
                subscription["student_info"]["birth_place"],
                subscription["student_info"]["identity_id"],
                subscription["student_info"]["national_id"],
                subscription.get("student_info", {}).get("date_validity_id", "-"),          # Date Validité
                start_date,                                                                 # Date entree = Date debut = jour de la rentrée scolaire
                start_date,                                                                 # Date 1ere entree = Date debut = jour de la rentrée scolaire
                subscription["student"]["email"],
                subscription["student"]["mobile_phone"],
                street_student,
                subscription["student"]["address"]["postal_code"],
                subscription["student"]["address"]["municipality"],
                subscription["student"]["address"]["locality"],
                "BE",                                                                       # Pays
                "O" if subscription["integration"] else "N",
                "O" if "is_cpu" in subscription and subscription["is_cpu"] else "N",
                subscription["health_comment"],                                             # Sante
                "O" if subscription["speech_therapist"] else "N",                           # logopede
                "F" if subscription["student_info"]["gender"] == "Femme" else "M",          # sexe
                student_id if student_id else "",                                           # matricule
                default_classe,                                                             # classe -> la classe de l'élève par défaut, selon son choix d'option
                orientation,                                                                # orientation
                "C",                                                                        # religion
                "N",                                                                        # langue 1
                "SMS",                                                                      # Envoi : deprecated, inutilisable en proeco
                "+",                                                                        # Correspondance : deprecated, inutilisable en proeco
                "OOONONNNONNNNN",                                                           # Papier/sms/mail
                "B",                                                                        # Zone
                "O" if subscription.get("fle_needed") else "N",                             # Besoin de FLE
            ]
            + data_father
            + data_mother
            + data_resp
            + data_free_address
            + data_last_school
        )

        # Préparation du la réponse : indique le type de réponse retournée (fichier text/csv)
        response = HttpResponse(
            content_type="text/csv",
        )
        # Préparation du la réponse : indique le nom du fichier retourné
        last_name = (
            unidecode(subscription["student"]["last_name"])
            .lower()
            .replace(" ", "-")
            .replace("'", "")
        )
        first_name = (
            unidecode(subscription["student"]["first_name"]).lower().replace(" ", "-")
        )
        response["Content-Disposition"] = (
            f'attachment; filename="inscription_{last_name}_{first_name}.xls"'
        )
        # Écrit dans la première ligne de la feuille nommée 'data' les éléments de l'objet 'columns', case après case
        for i, v in enumerate(columns):
            worksheet.write(0, i, v)
        # Écrit dans la deuxième ligne de la feuille nommée 'data' les éléments de l'objet 'data', case après case
        for i, v in enumerate(data):
            worksheet.write(1, i, v)

        # Sauvegarde le document .xls dans la réponse et retourne celle-ci
        workbook.save(response)
        return response
