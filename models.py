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

from django.db import models
from core.models import TeachingModel


class InscriptionSettingsModel(models.Model):
    teachings = models.ManyToManyField(TeachingModel, default=None)


class InscriptionModel(models.Model):
    uuid = models.UUIDField(unique=True)
    matricule = models.CharField(blank=True, max_length=10)         #
    subscription = models.JSONField()
    pending = models.BooleanField(default=False)
    is_validated = models.BooleanField()
    scholar_year = models.CharField(
        "Année scolaire",
        max_length=9,
        blank=True,
    )
    datetime_validation = models.DateTimeField(auto_now_add=True)
