require 'html/proofer'

# Test the build
desc "Build the site and test with HTML Proofer"
task :test do
  sh "bundle exec jekyll build"
  HTML::Proofer.new("./build", {:disable_external => true}).run
  # TODO: sh "scss-lint"
end
