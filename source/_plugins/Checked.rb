module Jekyll
  module Checked
    def checked(text)
      text.sub(/.*\//, '')
    end
  end
end

Liquid::Template.register_filter(Jekyll::Checked)