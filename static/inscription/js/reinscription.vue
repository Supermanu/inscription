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
    <BOverlay :show="loading">
        <BRow>
            <BCol>
                <BFormGroup>
                    <multiselect
                        ref="input"
                        v-model="search"
                        :show-no-options="false"
                        :internal-search="false"
                        :options="searchOptions"
                        :allow-empty="true"
                        placeholder="Rechercher un étudiant ou une classe"
                        select-label=""
                        selected-label="Sélectionné"
                        deselect-label=""
                        label="display"
                        track-by="id"
                        @search-change="getSearchOptions"
                        @select="selected"
                    >
                        <template #noResult>
                            Aucune personne ou classe trouvée.
                        </template>
                        <template #noOptions />
                    </multiselect>
                </BFormGroup>
            </BCol>
            <BCol>
                <BFormGroup>
                    <BFormCheckbox
                        v-model="onlyResubscribed"
                        switch
                        @change="getResubscription"
                    >
                        Montrer seulement les réinscriptions effectuées
                    </BFormCheckbox>
                    <BFormCheckbox
                        v-model="ownClasses"
                        switch
                        @change="getResubscription"
                    >
                        Montrer ses classes
                    </BFormCheckbox>
                </BFormGroup>
            </BCol>
        </BRow>
        <BRow>
            <BCol>
                <BTable
                    striped
                    bordered
                    head-variant="light"
                    hover
                    :items="resubscriptionsItems"
                    :fields="fields"
                >
                    <template #cell(student_id)="data">
                        <a
                            href="#"
                            @click="showStudentInfo(data.item.student_id)"
                        >
                            {{ data.item.student_id }}
                            <IBiTelephone />
                        </a>
                    </template>
                    <template #cell(actions)="data">
                        <BButton
                            size="sm"
                            :href="`${host}/resubscribe/?edit=true#/${data.item.student_id}/2024_last_minute/`"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            <IBiPencilSquare />
                        </BButton>
                        <BButton
                            size="sm"
                            href="#"
                            @click="showLink(data.item)"
                        >
                            <IBiLink />
                        </BButton>
                    </template>
                </BTable>
            </BCol>
        </BRow>
        <b-modal
            ref="studentinfo"
            size="lg"
            ok-only
        >
            <person-contact
                v-if="currentStudent"
                :custom-matricule="currentStudent"
            />
        </b-modal>
    </BOverlay>
</template>

<script>
import Multiselect from "vue-multiselect";
import "vue-multiselect/dist/vue-multiselect.min.css";

import { useModalController } from "bootstrap-vue-next";

import PersonContact from "@s:annuaire/js/contact_info.vue";

import axios from "axios";

export default {
    setup: function () {
        const { create } = useModalController();
        return { create };
    },
    components: {
        Multiselect,
        PersonContact,
    },
    data: function () {
        return {
            loading: true,
            onlyResubscribed: false,
            resubscriptions: [],
            resubscriptionsItems: [],
            // eslint-disable-next-line no-undef
            host: remoteUrl,
            search: "",
            ownClasses: true,
            fields: [
                {
                    key: "student_id",
                    label: "Matricule",
                },
                {
                    key: "last_name",
                    label: "Nom",
                },
                {
                    key: "first_name",
                    label: "Prénom",
                },
                {
                    key: "current_classe",
                    label: "Classe actuelle",
                    sortable: true,
                },
                {
                    key: "next_option",
                    label: "Option choisie",
                    sortable: true,
                    sortByFormatted: true,
                    formatter: (value, key, item) => {
                        if (!value) return "";

                        // const form = value.form ? value.form.form[0] : "";
                        // const channel = value.channel ? value.channel.channel[0] : "";
                        return `${item.next_year} ${this.getOption(value)}`;
                    },
                },
                {
                    key: "actions",
                    label: "",
                },
            ],
            searchId: -1,
            searchOptions: [],
            currentStudent: null,
            options: [],
        };
    },
    mounted: function () {
        this.getResubscription();
    },
    methods: {
        getOption: function (optionId) {
            if (!optionId) {
                return "";
            }
            const option = this.options.find(o => o.id === optionId);
            return `${option.form ? option.form.form[0] : ""} ${option.channel ? option.channel.channel[0] : ""} ${option.option}`;
        },
        showStudentInfo: function (student_id) {
            this.currentStudent = student_id;
            this.$refs.studentinfo.show();
        },
        showLink: function (item) {
            const link = `${this.host}/resubscribe/#/${item.student_id}/${item.random_key}/`;
            this.create({ body: link });
        },
        getResubscription: function () {
            this.loading = true;
            Promise.all([
                axios.get(
                    "/inscription/api/remote_server/resubscribe/api/resubscriberemote/",
                ),
                axios.get(
                    "/inscription/api/remote_server/subscribe/api/option/",
                ),
            ])
                .then((resps) => {
                    this.options = resps[1].data;
                    if (this.onlyResubscribed) {
                        this.resubscriptions = resps[0].data.results.filter(r => r.next_option);
                    } else {
                        this.resubscriptions = resps[0].data.results;
                    }

                    this.resubscriptionsItems = this.resubscriptions;
                    if (this.ownClasses) {
                        Promise.all(
                            // eslint-disable-next-line no-undef
                            user_properties.classes.map(c => axios.get(`/core/api/classe/${c}/`)),
                        ).then((classes) => {
                            this.resubscriptionsItems = this.resubscriptions.filter((resub) => {
                                return classes.map(c => `${c.data.year}${c.data.letter}`).includes(resub.current_classe);
                            });
                            this.loading = false;
                        });
                    } else {
                        this.loading = false;
                    }
                })
                .catch(() => {
                    this.loading = false;
                });
        },
        getSearchOptions: function (query) {
            if (!query) {
                this.searchOptions = [];
                return;
            }
            // Ensure the last search is the first response.
            this.searchId += 1;
            let currentSearch = this.searchId;

            axios.get(
                `/inscription/api/remote_server/resubscribe/api/resubscriberemote/?search=${query}`,
            )
                .then((resp) => {
                    if (this.searchId !== currentSearch)
                        return;

                    const results = this.onlyResubscribed ? resp.data.results.filter(r => r.next_option) : resp.data.results;
                    if (Number.isNaN(Number.parseInt(query[0]))) {
                        this.searchOptions = results.map((r) => {
                            return {
                                display: `${r.last_name} ${r.first_name} ${r.current_classe}`,
                                id: r.student_id,
                                type: "student",
                            };
                        });
                    } else {
                        this.searchOptions = [...new Set(results.map(r => r.current_classe))].map((c) => {
                            return {
                                display: c,
                                id: c,
                                type: "classe",
                            };
                        });
                    }
                });
        },
        selected: function (option) {
            if (option.type == "classe") {
                this.resubscriptionsItems = this.resubscriptions.filter(item => item.current_classe === option.id);
            } else {
                this.resubscriptionsItems = this.resubscriptions.filter(item => item.student_id === option.id);
            }
        },
    },
};
</script>
