/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Direct Print Action — Client-side raw printing via QZ Tray.
 *
 * Flow:
 *  1. Server generates raw data (ZPL/EPL) and returns ir.actions.client
 *  2. This component connects to QZ Tray on user's PC
 *  3. Sends raw data directly to the local USB/network printer
 *
 * QZ Tray must be installed & running: https://qz.io/download/
 */
export class DirectPrintAction extends Component {
    static template = "sm_direct_print.DirectPrintAction";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");

        onMounted(() => this._executePrint());
    }

    async _executePrint() {
        const params = this.props.action?.params || {};
        const rawData = params.raw_data || [];
        const printerName = params.printer_name || "";
        const jobName = params.job_name || "Print Job";
        const totalLabels = params.total_labels || rawData.length;

        if (!rawData.length) {
            this.notification.add("No data to print.", { type: "warning" });
            this._goBack();
            return;
        }

        if (typeof qz === "undefined") {
            this.notification.add(
                "QZ Tray not loaded. Install QZ Tray: https://qz.io/download/",
                { type: "danger", sticky: true }
            );
            this._goBack();
            return;
        }

        const startTime = Date.now();

        try {
            // Connect to QZ Tray
            if (!qz.websocket.isActive()) {
                this.notification.add("Connecting to QZ Tray...", { type: "info" });
                await qz.websocket.connect();
            }

            // Configure printer
            const config = qz.configs.create(printerName, { encoding: "UTF-8" });

            // Send all raw data as one print job
            const printData = rawData.map((data) => ({
                type: "raw",
                format: "plain",
                data: data,
            }));

            await qz.print(config, printData);

            const duration = Date.now() - startTime;

            this.notification.add(
                `${totalLabels} label(s) sent to ${printerName}`,
                { type: "success" }
            );

            // Log successful job
            this._logJob(params, "success", "", duration);

        } catch (err) {
            console.error("QZ Tray print error:", err);
            const duration = Date.now() - startTime;
            let message = String(err);

            if (message.includes("Unable to connect") || message.includes("WebSocket")) {
                message =
                    "Cannot connect to QZ Tray.\n\n" +
                    "Make sure:\n" +
                    "1. QZ Tray is installed (download: qz.io/download)\n" +
                    "2. QZ Tray is running (check system tray icon)\n" +
                    "3. Browser is not blocking WebSocket connections";
            } else if (message.includes("not found") || message.includes("No printer")) {
                message =
                    `Printer "${printerName}" not found on this PC.\n\n` +
                    "Make sure:\n" +
                    "1. Printer is powered on & connected\n" +
                    "2. Printer name in Odoo matches exactly\n" +
                    "   (Control Panel → Devices and Printers)";
            }

            this.notification.add(message, { type: "danger", sticky: true });

            // Log failed job
            this._logJob(params, "error", message, duration);
        }

        this._goBack();
    }

    async _logJob(params, state, errorMessage, durationMs) {
        try {
            await rpc("/direct_print/log_job", {
                printer_id: params.printer_id || false,
                template_id: params.template_id || false,
                job_name: params.job_name || "Print Job",
                label_count: params.total_labels || 0,
                state: state,
                error_message: errorMessage || "",
                duration_ms: durationMs || 0,
            });
        } catch (e) {
            console.warn("Failed to log print job:", e);
        }
    }

    _goBack() {
        this.action.restore();
    }
}

registry.category("actions").add("sm_direct_print.print_action", DirectPrintAction);
