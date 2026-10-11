package dev.evvie.waylandcraft.mixin;

import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LevelRenderer;

@Mixin(LevelRenderer.class)
public class LevelRendererMixin {

    @Shadow
    @Final
    private Minecraft minecraft;

    @Inject(method = "update", at = @At("HEAD"), cancellable = true)
    private void waylandcraft$guardNullPlayerOnUpdate(Camera camera, CallbackInfo ci) {
        if (this.minecraft == null || this.minecraft.player == null) {
            ci.cancel();
        }
    }
}
