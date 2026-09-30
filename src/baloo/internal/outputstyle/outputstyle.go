// Package outputstyle picks one of the plugin's Output styles for a project, in the Claude Code
// settings file of the project that enables the plugin, where none of Claude Code's settings files
// picks one already (ADR output-styles).
package outputstyle

import (
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Picked is an Output style Pick wrote: the file, and the Scope whose settings enable the plugin.
type Picked struct {
	Path    string
	Enabled settings.Scope
}

// Pick sets outputStyle to the plugin's `style` for the project at `project`, in the repo at
// `root`, where the plugin is enabled in its local, project or user settings, and none of Claude
// Code's settings files sets outputStyle already, to any value. It writes the file that enables
// the plugin: the project's settings.json or settings.local.json, or for the user's settings the
// project's settings.local.json. It returns what it wrote, a zero Picked when it wrote nothing. A
// file it creates goes into the repo's info/exclude, as Claude Code does with its own.
func Pick(project, root, style string) (Picked, error) {
	files := settings.Files(project)
	fields, err := settings.ReadAll(files)
	if err != nil {
		return Picked{}, err
	}
	for _, f := range fields {
		if _, ok := f["outputStyle"]; ok {
			return Picked{}, nil
		}
	}
	enabled := settings.Enabling(fields)
	if enabled == "" {
		return Picked{}, nil
	}
	path := files[settings.Local]
	if enabled == settings.Project {
		path = files[settings.Project]
	}
	created, err := settings.Set(path, "outputStyle", names.Plugin+":"+style)
	if err != nil {
		return Picked{}, err
	}
	picked := Picked{path, enabled}
	if created {
		return picked, settings.Exclude(root, path)
	}
	return picked, nil
}
