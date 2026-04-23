<!-- This file is part of Happyschool. -->
<!--  -->
<!-- Happyschool is the legal property of its developers, whose names -->
<!-- can be found in the AUTHORS file distributed with this source -->
<!-- distribution. -->
<!--  -->
<!-- Happyschool is free software: you can redistribute it and/or modify -->
<!-- it under the terms of the GNU Affero General Public License as published by -->
<!-- the Free Software Foundation, either version 3 of the License, or -->
<!-- (at your option) any later version. -->
<!--  -->
<!-- Happyschool is distributed in the hope that it will be useful, -->
<!-- but WITHOUT ANY WARRANTY; without even the implied warranty of -->
<!-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the -->
<!-- GNU Affero General Public License for more details. -->
<!--  -->
<!-- You should have received a copy of the GNU Affero General Public License -->
<!-- along with Happyschool.  If not, see <http://www.gnu.org/licenses/>. -->

<template>
    <div>
        <BContainer>
            <BRow>
                <BCol>
                    <h1>Inscription</h1>
                </BCol>
            </BRow>
            <BTabs content-class="mt-3">
                <BTab
                    title="Inscription"
                    active
                >
                    <BRow>
                        <BCol>
                            <BFormGroup
                                label="Rechercher un futur étudiant ou un parent/responsable"
                            >
                                <BFormInput
                                    v-model="search"
                                    @update:model-value="getSubscriptions"
                                />
                            </BFormGroup>
                        </BCol>
                        <BCol>
                            <BFormGroup>
                                <BFormCheckbox
                                    v-model="incomplete"
                                    switch
                                >
                                    Montrer les inscriptions non finies
                                </BFormCheckbox>
                            </BFormGroup>
                            <BFormGroup>
                                <BFormCheckbox
                                    v-model="pending"
                                    switch
                                >
                                    Inscriptions en attentes
                                </BFormCheckbox>
                            </BFormGroup>
                            <BButton-group>
                                <BButton
                                    v-if="canValidate"
                                    v-b-modal.stats
                                >
                                    Statistiques
                                </BButton>
                                <BButton
                                    v-b-modal.exportpdf
                                    variant="outline-primary"
                                >
                                    PDF
                                </BButton>
                                <BButton
                                    v-b-modal.errors
                                    variant="outline-danger"
                                >
                                    <BBadge variant="danger">
                                        {{ optionErrors.length }}
                                    </BBadge>
                                    Erreurs
                                </BButton>
                            </BButton-group>
                        </BCol>
                        <BCol md="3">
                            <BFormGroup>
                                <BFormSelect
                                    v-model="scholarYear"
                                    :options="scholarYearOptions"
                                    @update:model-value="getSubscriptions"
                                />
                            </BFormGroup>
                        </BCol>
                    </BRow>
                    <BRow>
                        <BCol>
                            <BOverlay :show="loading">
                                <BTable
                                    striped
                                    bordered
                                    head-variant="light"
                                    hover
                                    :items="subscriptions"
                                    :fields="fields"
                                    :tbody-tr-class="rowClass"
                                >
                                    <template #cell(pdf)="data">
                                        <a
                                            :href="`${host}/subscribe/pdf/${data.item.uuid}/`"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <IBiFileEarmarkText />
                                        </a>
                                        <a
                                            :href="`${host}/subscribe/?edit=true#/options/${data.item.uuid}/`"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <IBiPencilSquare />
                                        </a>
                                        <BFormCheckbox
                                            :checked="data.item.validation ? true: false"
                                            @change="aknowledge($event, data.item)"
                                        />
                                    </template>
                                    <template #cell(validation)="data">
                                        <span v-if="!incomplete && (!data.item.validation || !data.item.validation.is_validated)">
                                            <span v-if="isOptionFull(data.item.option.id, data.item.year)">
                                                <IBiExclamationTriangleFill variant="warning" />
                                                A mettre sur liste d'attente

                                                <BButton-group v-if="canValidate">
                                                    <BButton @click="pendingSubcription(data.item.uuid)">En attente</BButton>
                                                    <BButton @click="validateSubcription(data.item.uuid)">Valider</BButton>
                                                </BButton-group>
                                            </span>
                                            <span v-else-if="canValidate">
                                                <BButton @click="validateSubcription(data.item.uuid)">Valider</BButton>
                                            </span>
                                        </span>
                                        <span v-else-if="data.item.validation && data.item.validation.pending">
                                            En attente
                                            <span v-if="canValidate && isOptionFull(data.item.option.id, data.item.year)">
                                                <IBiExclamationTriangleFill variant="warning" />
                                                <BButton @click="confirmSubcription(data.item.uuid)">Valider</BButton>
                                            </span>
                                        </span>
                                        <span v-else-if="data.item.validation">
                                            {{ data.item.validation.matricule }}
                                            <a
                                                href="#"
                                                @click="exportSubscription(data.item.uuid)"
                                            >
                                                <IBiBoxArrowUpRight />
                                            </a>
                                        </span>
                                        <BButton
                                            v-if="canValidate"
                                            variant="danger"
                                            size="sm"
                                            @click="removeSubscription(data.item.uuid)"
                                        >
                                            <IBiTrash />
                                        </BButton>
                                        <span v-if="incomplete">
                                            <BButton
                                                size="sm"
                                                href="#"
                                                variant="warning"
                                                @click="markComplete(data.item)"
                                            >
                                                <IBiCheckAll />
                                            </BButton>
                                        </span>
                                    </template>
                                </BTable>
                                <BButton
                                    v-if="nextPage"
                                    variant="outline-primary"
                                    @click="showMoreSub"
                                >
                                    <IBiChevronDoubleDown />
                                    Plus d'inscriptions
                                </BButton>
                            </BOverlay>
                        </BCol>
                    </BRow>
                </BTab>
                <BTab
                    v-if="canValidate"
                    title="Réinscription"
                    lazy
                >
                    <resubscribe />
                </BTab>
                <template #tabs-end>
                    <BNavItem
                        :href="`https://inscription.idbbxl.com/subscribe/?from_user=${userName}`"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Formulaire inscription
                    </BNavItem>
                </template>
            </BTabs>
        </BContainer>
        <b-modal
            id="stats"
            ok-only
            size="lg"
        >
            <BListGroup>
                <BListGroupItem>
                    Nombre d'inscriptions validées : {{ subscriptionsValidatedCount }}
                </BListGroupItem>
                <BListGroupItem>
                    Nombre de réinscriptions : {{ resubCount }}
                </BListGroupItem>
                <BListGroupItem>
                    <strong>
                        Inscriptions validées par option
                        (<span class="text-primary">inscription</span> + <span class="text-secondary">réinscription</span>)
                    </strong>
                </BListGroupItem>
                <BListGroupItem
                    v-for="(option, index) in totalSubPerOption"
                    :key="option.uid"
                    :variant="option.count_sub + option.count_resub >= option.max_students ? 'warning' : ''"
                >
                    {{ isNaN(option.name[0]) ? option.year : "" }} {{ option.form[0] }}{{ option.channel[0] }} {{ option.name }}
                    : <strong>{{ option.count_sub + option.count_resub }}</strong>
                    (<span class="text-primary">{{ option.count_sub }}</span>
                    + <span class="text-secondary">{{ option.count_resub }}</span>)
                    / {{ option.max_students }}
                </BListGroupItem>
            </BListGroup>
        </b-modal>
        <b-modal
            id="errors"
            ok-only
            size="lg"
        >
            <BListGroup>
                <BListGroupItem
                    v-for="error in optionErrors"
                    :key="error.uuid"
                    href="#"
                    @click="search=error.subscription.student.last_name;getSubscriptions();$bvModal.hide('errors')"
                >
                    Élève: {{ error.subscription.student.last_name }} {{ error.subscription.student.first_name }}
                    (année : {{ error.subscription.study_year }}, option {{ error.subscription.study_option.option }})
                </BListGroupItem>
            </BListGroup>
        </b-modal>
        <b-modal
            id="exportpdf"
            ok-only
            @hidden="date_from=null;date_to=null;"
        >
            <BRow>
                <BCol>
                    <BFormRow>
                        <BFormGroup label="À partir du">
                            <input
                                v-model="date_from"
                                type="date"
                                :max="date_to"
                            >
                        </BFormGroup>
                    </BFormRow>
                </BCol>
                <BCol>
                    <BFormRow>
                        <BFormGroup label="Jusqu'au">
                            <input
                                v-model="date_to"
                                type="date"
                                :min="date_from"
                            >
                        </BFormGroup>
                    </BFormRow>
                </BCol>
            </BRow>
            <BFormRow>
                <BFormGroup label="Inscriptions non validées uniquement">
                    <BFormCheckbox
                        v-model="notValidatedOnly"
                    />
                </BFormGroup>
            </BFormRow>
            <BRow>
                <BCol>
                    <BButton
                        variant="primary"
                        :disabled="!date_from || !date_to"
                        :href="`/inscription/pdflist/${scholarYear}/${date_from}/${date_to}/${notValidatedOnly}/`"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Télécharger
                    </BButton>
                </BCol>
            </BRow>
        </b-modal>
    </div>
</template>

<script>
import axios from "axios";

import { useModalController } from "bootstrap-vue-next";

import Resubscribe from "./reinscription.vue";

const token = { xsrfCookieName: "csrftoken", xsrfHeaderName: "X-CSRFToken" };

export default {
    components: {
        Resubscribe,
    },
    setup: function () {
        const { create } = useModalController();
        return { create };
    },
    data: function () {
        return {
            incomplete: false,
            canValidate: false,
            // eslint-disable-next-line no-undef
            host: remoteUrl,
            search: "",
            searchId: 0,
            date_from: null,
            date_to: null,
            scholarYear: "",
            scholarYearOptions: [],
            fields: [
                {
                    key: "student",
                    label: "Étudiant",
                },
                {
                    key: "year",
                    label: "Future année",
                    formatter: (value, _, item) => {
                        return `${value} ${item.option.form ? item.option.form.form[0] : ""}${item.option.channel ? item.option.channel.channel[0] : ""}`;
                    },
                },
                {
                    key: "option",
                    label: "Option",
                    formatter: value => value.option,
                },
                {
                    key: "date",
                    label: "Date",
                },
                {
                    key: "father",
                    label: "Père",
                },
                {
                    key: "mother",
                    label: "Mère",
                },
                {
                    key: "other",
                    label: "Resp.",
                },
                {
                    key: "pdf",
                    label: "",
                },
                {
                    key: "validation",
                    label: "Mat.",
                },
            ],
            subscriptions: [],
            notsubPerOption: new Map(),
            totalSubPerOption: [],
            loading: false,
            nextPage: null,
            notValidatedOnly: true,
            optionErrors: [],
            pending: false,
        };
    },
    computed: {
        userName: function () {
            // eslint-disable-next-line no-undef
            return encodeURIComponent(menu.full_name);
        },
        subscriptionsValidatedCount: function () {
            return this.totalSubPerOption.reduce((pV, cV) => pV + cV.count_sub + cV.count_resub, 0);
        },
        resubCount: function () {
            return this.totalSubPerOption.reduce((pV, cV) => pV + cV.count_resub, 0);
        },
    },
    watch: {
        incomplete: function () {
            setTimeout(this.getSubscriptions(), 200);
        },
        pending: function () {
            setTimeout(this.getSubscriptions(), 200);
        },
    },
    mounted: function () {
        this.generateScholarYear();
        this.getSubscriptions();
        // eslint-disable-next-line no-undef
        this.canValidate = canValidate;

        window.onscroll = () => {
            const { scrollTop, scrollHeight, clientHeight }
                = document.documentElement;

            const bottomOfWindow = scrollHeight - scrollTop === clientHeight;
            if (bottomOfWindow && this.nextPage) {
                this.showMoreSub();
            }
        };
    },
    methods: {
        markComplete: function (item) {
            axios.post("/inscription/api/mark_complete/", { uuid: item.uuid }, token)
                .then(() => {
                    this.getSubscriptions();
                });
        },
        isOptionFull: function (optionId, year) {
            const option = this.totalSubPerOption.find(
                opt => opt.uid === `${optionId}_${year}`,
            );
            if (!option) {
                return false;
            }

            return option.count_sub + option.count_resub >= option.max_students;
        },
        rowClass: function (item, type) {
            if (!item || type !== "row") return;
            if (!item.is_completed) return "table-warning";
        },
        getNotValidatedPerOptions: function () {
            const options = this.subscriptions
                .filter(s => !s.validation)
                .map(s => `${s.option.id}_${s.year}`)
                .reduce(
                    (acc, e) => acc.set(e, (acc.get(e) || 0) + 1),
                    new Map(),
                );

            this.notsubPerOption = options;
        },
        aknowledge: function (checked, sub) {
            this.loading = true;
            if (checked) {
                const data = {
                    uuid: sub.uuid,
                    pending: false,
                    is_validated: false,
                    subscription: sub.dump,
                    scholar_year: this.scholarYear,
                };
                axios.post("/inscription/api/inscription/", data, token)
                    .then((resp) => {
                        sub.validation = resp.data;
                        this.loading = false;
                    })
                    .catch((err) => {
                        console.log(err);
                        this.loading = false;
                    });
            } else {
                axios.delete(`/inscription/api/inscription/${sub.validation.id}/`, token)
                    .then(() => {
                        this.getSubscriptions();
                    })
                    .catch((err) => {
                        console.log(err);
                        this.loading = false;
                    });
            }
        },
        removeSubscription: function (uuid) {
            this.create({
                body: "Êtes-vous sûr de vouloir supprimer définitevement l'inscription ?",
                centered: true,
                buttonSize: "sm",
                okVariant: "danger",
                okTitle: "Oui",
                cancelTitle: "Annuler",
            },
            )
                .then((remove) => {
                    if (!remove.ok) return;

                    this.loading = true;
                    const subIndex = this.subscriptions.findIndex(
                        s => s.uuid === uuid,
                    );
                    const validation = this.subscriptions[subIndex].validation;
                    let promises = [];
                    if (validation) {
                        promises.push(
                            axios.delete(
                                (`/inscription/api/inscription/${validation.id}/`,
                                token),
                            ),
                        );
                    }

                    const path = `subscribe/api/subscriptionremote/${this.subscriptions[subIndex].uuid}/`;
                    promises.push(
                        axios.delete(
                            `/inscription/api/remote_server/${path}`,
                            token,
                        ),
                    );
                    Promise.all(promises)
                        .then(() => {
                            this.getSubscriptions();
                        })
                        .catch(() => {
                            this.loading = false;
                        });
                });
        },
        validateSubcription: function (uuid) {
            this.loading = true;
            const sub = this.subscriptions.find(s => s.uuid === uuid);
            const send = sub.validation ? axios.put : axios.post;
            const data = sub.validation
                ? Object.assign({}, sub.validation, { pending: false, is_validated: true })
                : {
                    uuid: uuid,
                    pending: false,
                    is_validated: true,
                    subscription: sub.dump,
                    scholar_year: this.scholarYear,
                };
            send(`/inscription/api/inscription/${sub.validation ? sub.validation.id + "/" : ""}`, data, token)
                .then((resp) => {
                    sub.validation = resp.data;
                    this.loading = false;
                })
                .catch(() => {
                    this.loading = false;
                });
        },
        confirmSubcription: function (uuid) {
            this.loading = true;
            const sub = this.subscriptions.find(s => s.uuid === uuid);
            const id = sub.validation.id;
            const data = {
                uuid: uuid,
                pending: false,
                is_validated: true,
                subscription: sub.dump,
                scholar_year: this.scholarYear,
            };
            axios
                .put(`/inscription/api/inscription/${id}/`, data, token)
                .then((resp) => {
                    sub.validation = resp.data;
                    this.loading = false;
                })
                .catch(() => {
                    this.loading = false;
                });
        },
        pendingSubcription: function (uuid) {
            this.loading = true;
            const sub = this.subscriptions.find(s => s.uuid === uuid);
            const send = sub.validation ? axios.put : axios.post;
            const data = sub.validation
                ? Object.assign({}, sub.validation, { pending: true, is_validated: true })
                : {
                    uuid: uuid,
                    pending: true,
                    is_validated: true,
                    subscription: sub.dump,
                    scholar_year: this.scholarYear,
                };

            send(`/inscription/api/inscription/${sub.validation ? "/" + sub.validation.id + "/" : ""}`, data, token)
                .then((resp) => {
                    sub.validation = resp.data;
                    this.loading = false;
                })
                .catch(() => {
                    this.loading = false;
                });
        },
        exportSubscription: function (uuid) {
            const sub = this.subscriptions.find(s => s.uuid === uuid);
            const data = {
                subscription: sub.dump,
            };
            axios
                .patch(`/inscription/api/inscription/${sub.validation.id}/`, data, token)
                .then(() => {
                    window.location.href = `/inscription/export/${uuid}/`;
                });
        },
        getStats: function () {
            this.optionErrors = [];
            const requests = [
                axios.get("/inscription/api/remote_server/subscribe/api/option_by_year/?page_size=100"),
                axios.get(`/inscription/api/stats/${this.scholarYear}`),
            ];

            Promise.all(requests).then((resps) => {
                let errors = [];
                console.log(resps[0]);
                const options = resps[0].data.results.map((o) => {
                    return {
                        id: o.option.id,
                        uid: `${o.option.id}_${o.study_year}`,
                        name: o.option.option,
                        year: o.study_year,
                        form: o.option.form ? o.option.form.form : "",
                        channel: o.option.channel ? o.option.channel.channel : "",
                        count_sub: 0,
                        count_resub: 0,
                        max_students: o.max_students,
                    };
                });
                Object.entries(resps[1].data["sub_count"]).forEach((entry) => {
                    const index = options.findIndex(o => `${o.id}_${o.year}` === entry[0]);
                    if (index < 0) {
                        errors.push(entry[0].split("_"));
                        return;
                    }
                    options[index].count_sub += entry[1];
                });
                Object.entries(resps[1].data["resub_count"]).forEach((entry) => {
                    const index = options.findIndex(o => `${o.id}_${o.year}` === entry[0]);
                    if (index < 0) {
                        return;
                    }
                    options[index].count_resub += entry[1];
                });
                this.totalSubPerOption = options;

                // Get subscriptions with errors
                const promises = errors.map((e) => {
                    return axios.get(`/inscription/api/inscription/?subscription__study_option__id=${e[0]}&subscription__study_year=${e[1]}&scholar_year=${this.scholarYear}&is_validated=True`);
                });

                Promise.all(promises)
                    .then((resps) => {
                        this.optionErrors = resps.map(r => r.data.results).flat();
                    });
            });
        },
        getSubscriptions: function () {
            this.loading = true;
            this.getStats();
            this.searchId += 1;
            let currentSearch = this.searchId;
            axios
                .get(
                    `/inscription/api/list/1/${
                        this.incomplete ? "false" : "true"
                    }/${this.scholarYear}/${this.pending}/${this.search}`,
                )
                .then((resp) => {
                    if (this.searchId !== currentSearch)
                        return;
                    this.subscriptions = resp.data.results;
                    this.nextPage = resp.data.next;
                    this.loading = false;
                })
                .catch((err) => {
                    console.log(err);
                    this.loading = false;
                });
        },
        generateScholarYear: function () {
            const currentYear = new Date().getFullYear();
            const currentMonth = new Date().getMonth();
            // Scholar change would be in April.
            const currentScholarYear
                = currentMonth < 8 ? currentYear - 1 : currentYear;

            this.scholarYearOptions = [
                `${currentScholarYear}-${currentScholarYear + 1}`,
                `${currentScholarYear + 1}-${currentScholarYear + 2}`,
            ];

            // After April (3), set next scholar year as default.
            this.scholarYear = currentMonth < 3 || currentMonth >= 8
                ? `${currentScholarYear}-${currentScholarYear + 1}`
                : `${currentScholarYear + 1}-${currentScholarYear + 2}`;
        },
        showMoreSub: function () {
            const nextPage = new URL(this.nextPage).searchParams.get(
                "page",
            );
            this.loading = true;
            axios
                .get(
                    `/inscription/api/list/${nextPage}/${
                        this.incomplete ? "false" : "true"
                    }/${this.scholarYear}/${this.pending}/${this.search}`,
                )
                .then((resp) => {
                    this.subscriptions = this.subscriptions.concat(
                        resp.data.results,
                    );
                    this.nextPage = resp.data.next;
                    this.loading = false;
                })
                .catch((err) => {
                    console.log(err);
                    this.loading = false;
                });
        },
    },
};
</script>

<style>
</style>
