"use strict";

var $table = $("#records");
var $details = $("#details");
var registrationId = $table.data("reg");
var baseUrl = `/api/registration/${registrationId}`

var buildGrid = function (columns) {
    $table.jqGrid({
        url: `${baseUrl}/records/`,
        edit: true,
        altRows: true,
        autowidth: false,
        rowid: "id",
        caption: "",
        colModel: columns,
        datatype: 'json',
        footerrow: true,
        gridview: true,
        guiStyle: "jQueryUI",
        height: 300,
        hoverrows: true,
        loadonce: false,
        // iconSet: "fontAwesome",
        // multikey: "altKey",
        multiselect: false,
        pager: '#dataTablePager',
        pgbuttons: true,
        // pgtext: null,
        prmNames: {nd: null},
        recordpos: 'left',
        rowNum: 30,
        rownumbers: true,
        rownumWidth: 20,
        viewrecords: true,
        width: 900,
        jsonReader: {
            id: 'id',
            repeatitems: false,
            root: 'results',
            page: 'page',
            total: function (obj) {
                Math.floor(obj.count)
            },
            userdata: function (obj) {
                var ret = {};
                for (var i in obj.results) {
                    ret[obj.results[i].id] = obj.results[i].flatten;
                }
                return ret
            }
        },
        gridComplete: function () {
            $(".ui-jqgrid-sortable").css('white-space', 'normal');
        },
        onSelectRow: function (rowid) {
            var userdata = $table.getGridParam('userData');
            $details.html("");
            var details = userdata[rowid];
            for (const key in details) {
                $details.append(`<div class="font-bold capitalize">${key}</div>`)
                $details.append(`<div class="mb-3">${details[key]}</div>`)
            }
        },
    });
}// buildGrid

$.ajax({
    url: `${baseUrl}/metadata/`,
    success: function (data) {
        var columns = [{name: "id", label: "#", width: "40", align: "right"},
            {name: "timestamp", label: "Timestamp", formatter: 'date', width: "70"},
            {name: "remote_ip", label: "Remote IP", width: "70"},
        ];
        for (var f in data.base.fields) {
            columns.push({
                name: data.base.fields[f].name,
                label: data.base.fields[f].label,
            })
        }
        buildGrid(columns);
    } // success
});
