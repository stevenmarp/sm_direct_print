/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class PrintDashboard extends Component {
    static template = "sm_direct_print.PrintDashboard";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.state = useState({
            data: null,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/direct_print/dashboard");
        } catch (e) {
            console.error("Dashboard load error:", e);
        }
        this.state.loading = false;
    }

    openPrinters() {
        this.action.doAction("sm_direct_print.direct_printer_action");
    }

    openTemplates() {
        this.action.doAction("sm_direct_print.label_template_action");
    }

    openPrintHistory() {
        this.action.doAction("sm_direct_print.print_job_action");
    }

    getStateClass(state) {
        if (state === "success") return "badge bg-success";
        if (state === "error") return "badge bg-danger";
        return "badge bg-info";
    }

    getStateLabel(state) {
        if (state === "success") return "Success";
        if (state === "error") return "Error";
        return "Sent";
    }
}

registry.category("actions").add("sm_direct_print.print_dashboard", PrintDashboard);
