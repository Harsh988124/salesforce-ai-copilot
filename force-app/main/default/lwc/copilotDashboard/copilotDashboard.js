import { LightningElement, api, track } from 'lwc';

export default class CopilotDashboard extends LightningElement {
    @api recordId; 
    accountId = '';
    
    // @track makes the UI reactively update when these variables change
    @track copilotResult = null;
    @track error = null;
    isLoading = false;

    connectedCallback() {
        if (this.recordId) {
            this.accountId = this.recordId;
        }
    }

    handleInputChange(event) {
        this.accountId = event.target.value;
    }

    async runCopilot() {
        if (!this.accountId) {
            this.error = "Please enter an Account ID.";
            return;
        }

        this.isLoading = true;
        this.error = null;
        this.copilotResult = null;

        try {
            // Note: Check your app/main.py. If the route has a trailing slash 
            // at the end, make sure to add it here too!
            const response = await fetch(`http://localhost:8001/copilot/analyze/${this.accountId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include' // <-- CRITICAL: Tells browser to send your Salesforce session
            });

            if (!response.ok) {
                // This will extract the exact reason from FastAPI (e.g., 401 Unauthorized)
                const errorDetails = await response.text(); 
                throw new Error(`HTTP Error ${response.status}:${errorDetails}`);
            }

            this.copilotResult = await response.json();
            console.log('Successfully fetched Copilot Data:', this.copilotResult);
            
        } catch (err) {
            console.error('Error fetching copilot data:', err);
            this.error = `Connection failed: ${err.message}`;
        } finally {
            this.isLoading = false;
        }
    }
}