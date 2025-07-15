#include <wx/wx.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <thread>
#include <cstdio>      // For popen
#include <sys/types.h> // For pid_t
#include <string>

using json = nlohmann::json;

// Helper function to get the absolute path to bot directory (relative to exe)
std::filesystem::path getBotDir()
{
    auto exeDir = std::filesystem::current_path();
    return std::filesystem::absolute(exeDir / "../../bot");
}

class ConfigEditorFrame : public wxFrame
{
public:
    ConfigEditorFrame()
        : wxFrame(nullptr, wxID_ANY, "Config Editor", wxDefaultPosition, wxSize(700, 600)), botPid_(0)
    {
        wxPanel *panel = new wxPanel(this);
        wxBoxSizer *sizer = new wxBoxSizer(wxVERTICAL);

        adminCtrl_ = new wxTextCtrl(panel, wxID_ANY);
        botLogsIdCtrl_ = new wxTextCtrl(panel, wxID_ANY);
        botUserIdCtrl_ = new wxTextCtrl(panel, wxID_ANY);
        dChannelIdCtrl_ = new wxTextCtrl(panel, wxID_ANY);
        timezoneCtrl_ = new wxTextCtrl(panel, wxID_ANY);
        tokenCtrl_ = new wxTextCtrl(panel, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, wxTE_PASSWORD);
        jobsBox_ = new wxListBox(panel, wxID_ANY);

        delButton_ = new wxButton(panel, wxID_ANY, "Delete Job");
        saveButton_ = new wxButton(panel, wxID_ANY, "Save Config");
        startButton_ = new wxButton(panel, wxID_ANY, "Start Bot");
        stopButton_ = new wxButton(panel, wxID_ANY, "Stop Bot");

        // Layout
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Admin user ID:"), 0, wxALL, 5);
        sizer->Add(adminCtrl_, 0, wxALL | wxEXPAND, 5);
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Bot-logs channel ID:"), 0, wxALL, 5);
        sizer->Add(botLogsIdCtrl_, 0, wxALL | wxEXPAND, 5);
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Bot user ID:"), 0, wxALL, 5);
        sizer->Add(botUserIdCtrl_, 0, wxALL | wxEXPAND, 5);
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Default channel ID:"), 0, wxALL, 5);
        sizer->Add(dChannelIdCtrl_, 0, wxALL | wxEXPAND, 5);
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Timezone:"), 0, wxALL, 5);
        sizer->Add(timezoneCtrl_, 0, wxALL | wxEXPAND, 5);
        sizer->Add(new wxStaticText(panel, wxID_ANY, "Token:"), 0, wxALL, 5);
        sizer->Add(tokenCtrl_, 0, wxALL | wxEXPAND, 5);

        sizer->Add(jobsBox_, 1, wxALL | wxEXPAND, 5);
        sizer->Add(delButton_, 0, wxALL, 5);
        sizer->Add(saveButton_, 0, wxALL, 5);
        sizer->Add(startButton_, 0, wxALL, 5);
        sizer->Add(stopButton_, 0, wxALL, 5);

        panel->SetSizer(sizer);

        // Events
        delButton_->Bind(wxEVT_BUTTON, &ConfigEditorFrame::OnDeleteJob, this);
        saveButton_->Bind(wxEVT_BUTTON, &ConfigEditorFrame::OnSaveConfig, this);
        startButton_->Bind(wxEVT_BUTTON, &ConfigEditorFrame::OnStartBot, this);
        stopButton_->Bind(wxEVT_BUTTON, &ConfigEditorFrame::OnStopBot, this);

        LoadJobsFromConfig();
    }

    void static StartBotInThread(const std::string &pythonPath, const std::string &botScript)
    {
        // Build a background command
        std::string cmd = pythonPath + " " + botScript + " &";
        std::system(cmd.c_str());
    }

private:
    std::vector<json> jobsList_;
    wxListBox *jobsBox_;
    wxTextCtrl *adminCtrl_, *botLogsIdCtrl_, *botUserIdCtrl_, *dChannelIdCtrl_, *timezoneCtrl_, *tokenCtrl_;
    wxButton *addButton_, *delButton_, *saveButton_, *startButton_, *stopButton_;
    pid_t botPid_;
    int selectedJob_ = -1;

    void ReadBotPID()
    {
        auto pidFile = "bot.pid";
        std::ifstream ifs(pidFile);
        if (!ifs)
        {
            wxMessageBox("Could not open bot.pid. Is the bot running?", "Error", wxICON_ERROR);
            botPid_ = 0;
            return;
        }
        std::string line;
        std::getline(ifs, line);
        ifs.close();
        try
        {
            botPid_ = std::stol(line); // or std::stoi, but PIDs can be large
        }
        catch (...)
        {
            wxMessageBox("Could not parse bot.pid.", "Error", wxICON_ERROR);
            botPid_ = 0;
        }
    }

    void LoadJobsFromConfig()
    {
        jobsList_.clear();
        jobsBox_->Clear();

        // Build the absolute path to config.json
        auto configPath = getBotDir() / "scheduler.json";
        std::ifstream ifs(configPath);
        if (!ifs)
        {
            wxMessageBox("Could not open config.json!", "Error", wxICON_ERROR);
            return;
        }
        json cfg;
        ifs >> cfg;
        ifs.close();

        if (cfg.contains("jobs"))
        {
            for (const auto &job : cfg["jobs"])
            {
                jobsList_.push_back(job);
                wxString summary = wxString::Format(
                    "%s [%s]: %s",
                    job.value("id", "NO_ID"),
                    job.value("cron", "-"),
                    job.value("message", "-"));
                jobsBox_->Append(summary);
            }
        }
    }

    void OnSaveConfig(wxCommandEvent &)
    {
        try
        {
            json cfg;
            cfg["token"] = tokenCtrl_->GetValue().ToStdString();
            cfg["default_channel_id"] = std::stoll(dChannelIdCtrl_->GetValue().ToStdString());
            cfg["bot_logs_channel_id"] = std::stoll(botLogsIdCtrl_->GetValue().ToStdString());
            cfg["admin_user_id"] = std::stoll(adminCtrl_->GetValue().ToStdString());
            cfg["bot_user_id"] = std::stoll(botUserIdCtrl_->GetValue().ToStdString());
            cfg["timezone"] = timezoneCtrl_->GetValue().ToStdString();

            // Write directly to bot/config.json using an absolute path
            auto configPath = getBotDir() / "config.json";
            std::ofstream ofs(configPath);
            ofs << cfg.dump(4);
            ofs.close();

            wxMessageBox("Configuration saved successfully!", "Success");
        }
        catch (const std::exception &ex)
        {
            wxMessageBox(wxString::Format("Error saving config: %s", ex.what()), "Error", wxICON_ERROR);
        }
    }

    void OnDeleteJob(wxCommandEvent &)
    {
        int idx = jobsBox_->GetSelection();
        if (idx == wxNOT_FOUND || idx >= int(jobsList_.size()))
            return;

        // Remove from both list and UI
        jobsList_.erase(jobsList_.begin() + idx);
        jobsBox_->Delete(idx);

        // Persist the *entire* updated list:
        SaveAllJobsToDisk();

        // Clear any selection state
        selectedJob_ = -1;
    }

    void SaveAllJobsToDisk()
    {
        // Build a JSON containing all remaining jobs
        json cfg;
        cfg["jobs"] = jobsList_;

        auto path = getBotDir() / "scheduler.json";
        std::ofstream ofs(path);
        ofs << cfg.dump(4);

        wxMessageBox("Jobs saved successfully!", "Success");
    }

    void OnStartBot(wxCommandEvent &)
    {
        auto botDir = getBotDir();
        std::filesystem::current_path(botDir);

        std::string pythonPath = (botDir / ".venv/bin/python").string();
        std::string botScript = (botDir / "bot.py").string();

        // Start the bot in a separate thread so the UI doesn't freeze
        std::thread(StartBotInThread, pythonPath, botScript).detach();
        wxMessageBox("Bot started!", "Info");
    }

    void OnStopBot(wxCommandEvent &)
    {
        ReadBotPID(); // Read the PID after starting the bot
        if (botPid_ == 0)
        {
            wxMessageBox("No bot was started from this app.", "Error", wxICON_ERROR);
            return;
        }
        std::string killCmd = "kill " + std::to_string(botPid_);
        int result = std::system(killCmd.c_str());
        if (result == 0)
            wxMessageBox("Bot stopped.", "Info");
        else
            wxMessageBox("Failed to stop bot (maybe it wasn't running).", "Error", wxICON_ERROR);

        botPid_ = 0;
    }
};

class MyApp : public wxApp
{
public:
    bool OnInit() override
    {
        ConfigEditorFrame *frame = new ConfigEditorFrame();
        frame->Show();
        return true;
    }
};

wxIMPLEMENT_APP(MyApp);
