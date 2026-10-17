Rename the owner's `telephone` field to `phone` everywhere in the app: the model, the store (including the keyword
arguments that set it), the CLI, every other module that reads it, and the validation messages. Data files written
before this change say "telephone"; they must still load. Files saved from now on must say "phone".
